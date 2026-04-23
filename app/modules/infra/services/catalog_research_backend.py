from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request

from app.core.exceptions import BusinessRuleError

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.getenv("CATALOG_RESEARCH_MODEL") or os.getenv("CLAUDE_MODEL") or "claude-sonnet-4-5"
DEFAULT_BACKEND = (os.getenv("CATALOG_RESEARCH_BACKEND") or "http").strip().lower()
MCP_TOOL = os.getenv("CATALOG_RESEARCH_MCP_TOOL") or "catalog_research.lookup_hardware"
MCP_SERVER = os.getenv("CATALOG_RESEARCH_MCP_SERVER") or ""

SYSTEM_PROMPT = (
    "You are a careful IT hardware catalog researcher. "
    "Return strict JSON only. Prefer vendor datasheets, product pages, and official lifecycle notices. "
    "If uncertain, return null instead of guessing."
)

PROMPT_TEMPLATE = """Research the following hardware catalog product and return normalized JSON only.

Vendor: {vendor}
Model: {name}
Existing reference URL: {reference_url}
Classification: {classification}
Existing known hardware spec summary:
- size_unit: {size_unit}
- power_count: {power_count}
- power_type: {power_type}
- power_watt: {power_watt}

Return this exact JSON shape:
{{
  "confidence": "high|medium|low",
  "hardware_spec": {{
    "size_unit": 1,
    "width_mm": null,
    "height_mm": null,
    "depth_mm": null,
    "weight_kg": null,
    "power_count": null,
    "power_type": null,
    "power_watt": null,
    "cpu_summary": null,
    "memory_summary": null,
    "throughput_summary": null,
    "os_firmware": null,
    "spec_url": null
  }},
  "eosl": {{
    "eos_date": "YYYY-MM-DD or null",
    "eosl_date": "YYYY-MM-DD or null",
    "eosl_note": null,
    "source_url": null
  }},
  "interfaces": [
    {{
      "interface_type": "GE RJ45",
      "speed": "1G",
      "count": 8,
      "connector_type": "RJ-45",
      "capacity_type": "fixed",
      "note": null
    }}
  ],
  "uncertain_fields": ["field names that still need verification"]
}}

Rules:
- Use null when unknown.
- size_unit must be integer rack unit if known.
- interfaces should describe base/default onboard or appliance ports, not optional add-on cards unless clearly default.
- capacity_type must be one of fixed, base, max.
- eos/eosl dates must be ISO format only.
- uncertain_fields should contain names like size_unit, power_count, eosl_date, interfaces.
- Never wrap in markdown.
"""


def _api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if not key:
        raise BusinessRuleError("카탈로그 조사용 ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다.", status_code=503)
    return key


def _extract_json_payload(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    raw = match.group(0) if match else cleaned
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BusinessRuleError(f"카탈로그 조사 응답 JSON 파싱 실패: {exc}", status_code=502)


def _run_http_research(prompt: str) -> dict:
    payload = {
        "model": DEFAULT_MODEL,
        "max_tokens": 1800,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": _api_key(),
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise BusinessRuleError(f"카탈로그 조사 API 호출 실패: {detail or exc.reason}", status_code=502)
    except urllib.error.URLError as exc:
        raise BusinessRuleError(f"카탈로그 조사 API 연결 실패: {exc.reason}", status_code=502)

    content = body.get("content") or []
    text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not text:
        raise BusinessRuleError("카탈로그 조사 응답이 비어 있습니다.", status_code=502)
    return _extract_json_payload(text)


def _run_mcp_research(args: dict) -> dict:
    mcporter = shutil.which("mcporter")
    if not mcporter:
        raise BusinessRuleError("MCP research backend를 쓰려면 mcporter가 설치되어 있어야 합니다.", status_code=503)

    selector = MCP_TOOL
    if MCP_SERVER:
        selector = f"{MCP_SERVER}.{MCP_TOOL.split('.')[-1]}" if "." not in MCP_SERVER else MCP_SERVER
    cmd = [mcporter, "call", selector, "--args", json.dumps(args, ensure_ascii=False), "--output", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        raise BusinessRuleError("MCP catalog research 호출 시간이 초과되었습니다.", status_code=504)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise BusinessRuleError(f"MCP catalog research 호출 실패: {detail or 'unknown error'}", status_code=502)
    text = (proc.stdout or "").strip()
    if not text:
        raise BusinessRuleError("MCP catalog research 응답이 비어 있습니다.", status_code=502)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _extract_json_payload(text)
    if isinstance(parsed, dict) and "result" in parsed and isinstance(parsed["result"], dict):
        return parsed["result"]
    return parsed


def run_catalog_research(args: dict) -> dict:
    backend = DEFAULT_BACKEND
    if backend == "mcp":
        return _run_mcp_research(args)
    if backend == "http":
        prompt = PROMPT_TEMPLATE.format(**args)
        return _run_http_research(prompt)
    raise BusinessRuleError(f"지원하지 않는 catalog research backend입니다: {backend}", status_code=500)

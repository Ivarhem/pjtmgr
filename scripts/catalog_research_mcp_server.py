#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("CATALOG_RESEARCH_MODEL") or os.getenv("CLAUDE_MODEL") or "claude-sonnet-4-5"
SERVER_NAME = "catalog-research"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"

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

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string"},
        "name": {"type": "string"},
        "reference_url": {"type": ["string", "null"]},
        "classification": {"type": ["string", "null"]},
        "size_unit": {"type": ["integer", "number", "null"]},
        "power_count": {"type": ["integer", "number", "null"]},
        "power_type": {"type": ["string", "null"]},
        "power_watt": {"type": ["integer", "number", "null"]},
    },
    "required": ["vendor", "name"],
    "additionalProperties": True,
}


def _api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if not key:
        raise RuntimeError("카탈로그 조사용 ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다.")
    return key


def _extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    raw = match.group(0) if match else cleaned
    return json.loads(raw)


def _call_anthropic(prompt: str) -> dict[str, Any]:
    payload = {
        "model": MODEL,
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
        raise RuntimeError(f"카탈로그 조사 API 호출 실패: {detail or exc.reason}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"카탈로그 조사 API 연결 실패: {exc.reason}")

    content = body.get("content") or []
    text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not text:
        raise RuntimeError("카탈로그 조사 응답이 비어 있습니다.")
    try:
        return _extract_json_payload(text)
    except Exception as exc:
        raise RuntimeError(f"카탈로그 조사 응답 JSON 파싱 실패: {exc}")


def lookup_hardware(arguments: dict[str, Any]) -> dict[str, Any]:
    prompt = PROMPT_TEMPLATE.format(
        vendor=arguments.get("vendor") or "",
        name=arguments.get("name") or "",
        reference_url=arguments.get("reference_url") or "none",
        classification=arguments.get("classification") or "unknown",
        size_unit=arguments.get("size_unit"),
        power_count=arguments.get("power_count"),
        power_type=arguments.get("power_type"),
        power_watt=arguments.get("power_watt"),
    )
    return _call_anthropic(prompt)


def read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("utf-8").partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    payload = sys.stdin.buffer.read(length)
    if not payload:
        return None
    return json.loads(payload.decode("utf-8"))


def send_message(message: dict[str, Any]) -> None:
    body = json.dumps(message, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def success(msg_id: Any, result: dict[str, Any]) -> None:
    send_message({"jsonrpc": "2.0", "id": msg_id, "result": result})


def error(msg_id: Any, message: str, code: int = -32000) -> None:
    send_message({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


def handle_request(request: dict[str, Any]) -> None:
    method = request.get("method")
    msg_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        success(msg_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
        return

    if method == "notifications/initialized":
        return

    if msg_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return

    if msg_id is None and isinstance(method, str) and method.startswith("$/"):
        return

    if method == "ping":
        success(msg_id, {})
        return

    if method == "tools/list":
        success(msg_id, {
            "tools": [{
                "name": "lookup_hardware",
                "description": "Research hardware catalog specs and EOS/EOSL information from vendor/model metadata.",
                "inputSchema": INPUT_SCHEMA,
            }]
        })
        return

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name != "lookup_hardware":
            error(msg_id, f"Unknown tool: {name}", -32601)
            return
        try:
            result = lookup_hardware(arguments)
        except Exception as exc:
            success(msg_id, {
                "content": [{"type": "text", "text": str(exc)}],
                "isError": True,
            })
            return
        success(msg_id, {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            "structuredContent": result,
        })
        return

    if msg_id is None:
        return
    error(msg_id, f"Method not found: {method}", -32601)


def main() -> int:
    while True:
        request = read_message()
        if request is None:
            return 0
        handle_request(request)


if __name__ == "__main__":
    raise SystemExit(main())

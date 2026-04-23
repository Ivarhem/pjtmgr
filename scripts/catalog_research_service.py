#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.getenv("CATALOG_RESEARCH_MODEL") or os.getenv("CLAUDE_MODEL") or os.getenv("CODEX_MODEL") or "claude-sonnet-4-5"
SERVICE_TOKEN = (os.getenv("CATALOG_RESEARCH_SERVICE_TOKEN") or "").strip()
HOST = os.getenv("CATALOG_RESEARCH_SERVICE_HOST") or "0.0.0.0"
PORT = int(os.getenv("CATALOG_RESEARCH_SERVICE_PORT") or "8765")
PROVIDER = (os.getenv("CATALOG_RESEARCH_PROVIDER") or "anthropic").strip().lower()
CODEX_BIN = os.getenv("CATALOG_RESEARCH_CODEX_BIN") or "codex"
CODEX_MODEL = (os.getenv("CATALOG_RESEARCH_CODEX_MODEL") or os.getenv("CODEX_MODEL") or "").strip()
CODEX_WORKDIR = os.getenv("CATALOG_RESEARCH_CODEX_WORKDIR") or "/tmp"
CODEX_TIMEOUT = int(os.getenv("CATALOG_RESEARCH_CODEX_TIMEOUT") or "90")
CODEX_AUTH_SRC = Path(os.getenv("CATALOG_RESEARCH_CODEX_AUTH_SRC") or "/run/catalog-research-secrets/codex-auth.json")
CODEX_HOME = Path.home() / ".codex"

SYSTEM_PROMPT = (
    "You are a careful IT hardware catalog researcher. "
    "Return strict JSON only. Prefer vendor datasheets, product pages, and official lifecycle notices. "
    "If uncertain, return null instead of guessing."
)

ANTHROPIC_PROMPT_TEMPLATE = """Research the following hardware catalog product and return normalized JSON only.

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


class LookupHardwareRequest(BaseModel):
    vendor: str
    name: str
    reference_url: str | None = None
    classification: str | None = None
    size_unit: int | float | None = None
    power_count: int | float | None = None
    power_type: str | None = None
    power_watt: int | float | None = None


app = FastAPI(title="catalog-research-service", version="0.2.3")


def _api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail="카탈로그 조사용 ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다.")
    return key


def _verify_auth(authorization: str | None) -> None:
    if not SERVICE_TOKEN:
        return
    expected = f"Bearer {SERVICE_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="invalid authorization token")


def _extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    raw = match.group(0) if match else cleaned
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"카탈로그 조사 응답 JSON 파싱 실패: {exc}")


def _anthropic_prompt_from_args(args: LookupHardwareRequest) -> str:
    return ANTHROPIC_PROMPT_TEMPLATE.format(
        vendor=args.vendor or "",
        name=args.name or "",
        reference_url=args.reference_url or "none",
        classification=args.classification or "unknown",
        size_unit=args.size_unit,
        power_count=args.power_count,
        power_type=args.power_type,
        power_watt=args.power_watt,
    )


def _codex_prompt_from_args(args: LookupHardwareRequest) -> str:
    return (
        'Return strict JSON only with this exact top-level shape: '
        '{"confidence":"high|medium|low","hardware_spec":{"size_unit":null,"spec_url":null},'
        '"eosl":{"eos_date":null,"eosl_date":null,"source_url":null},'
        '"interfaces":[],"uncertain_fields":[]} '
        f'Research vendor="{args.vendor}" model="{args.name}". '
        'Use built-in knowledge only. No prose. '
        'If unsure, return null or add the field name to uncertain_fields.'
    )


def _normalize_codex_result(data: dict[str, Any]) -> dict[str, Any]:
    result = {
        "confidence": data.get("confidence") if data.get("confidence") in {"high", "medium", "low"} else "low",
        "hardware_spec": data.get("hardware_spec") if isinstance(data.get("hardware_spec"), dict) else {},
        "eosl": data.get("eosl") if isinstance(data.get("eosl"), dict) else {},
        "interfaces": data.get("interfaces") if isinstance(data.get("interfaces"), list) else [],
        "uncertain_fields": data.get("uncertain_fields") if isinstance(data.get("uncertain_fields"), list) else [],
    }
    hs = result["hardware_spec"]
    if hs.get("size_unit") in {"RU", "1RU", "1U", "2RU", "2U"}:
        m = re.search(r"(\d+)", str(hs["size_unit"]))
        hs["size_unit"] = int(m.group(1)) if m else None
    elif hs.get("size_unit") is not None:
        try:
            hs["size_unit"] = int(hs["size_unit"])
        except Exception:
            hs["size_unit"] = None
    hs.setdefault("spec_url", None)
    eosl = result["eosl"]
    eosl.setdefault("eos_date", None)
    eosl.setdefault("eosl_date", None)
    eosl.setdefault("source_url", None)
    normalized_interfaces: list[dict[str, Any]] = []
    for item in result["interfaces"]:
        if isinstance(item, dict):
            normalized_interfaces.append(item)
        elif isinstance(item, str):
            normalized_interfaces.append({"interface_type": item, "speed": None, "count": None, "connector_type": None, "capacity_type": None, "note": None})
    result["interfaces"] = normalized_interfaces
    result["uncertain_fields"] = [str(x) for x in result["uncertain_fields"]]
    return result


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
        raise HTTPException(status_code=502, detail=f"카탈로그 조사 API 호출 실패: {detail or exc.reason}")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"카탈로그 조사 API 연결 실패: {exc.reason}")

    content = body.get("content") or []
    text = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not text:
        raise HTTPException(status_code=502, detail="카탈로그 조사 응답이 비어 있습니다.")
    return _extract_json_payload(text)


def _prepare_codex_auth() -> None:
    CODEX_HOME.mkdir(parents=True, exist_ok=True)
    target = CODEX_HOME / "auth.json"
    if not CODEX_AUTH_SRC.exists():
        raise HTTPException(status_code=503, detail=f"Codex auth 파일을 찾을 수 없습니다: {CODEX_AUTH_SRC}")
    src_bytes = CODEX_AUTH_SRC.read_bytes()
    if not target.exists() or target.read_bytes() != src_bytes:
        target.write_bytes(src_bytes)
        target.chmod(0o600)


def _call_codex(prompt: str) -> dict[str, Any]:
    codex = shutil.which(CODEX_BIN) if os.path.sep not in CODEX_BIN else (CODEX_BIN if os.path.exists(CODEX_BIN) else None)
    if not codex:
        raise HTTPException(status_code=503, detail=f"Codex CLI를 찾을 수 없습니다: {CODEX_BIN}")

    _prepare_codex_auth()
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as f:
        output_path = f.name
    cmd = [codex, "exec", "--skip-git-repo-check", "--sandbox", "read-only"]
    if CODEX_MODEL:
        cmd.extend(["--model", CODEX_MODEL])
    cmd.extend(["--output-last-message", output_path, prompt])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CODEX_TIMEOUT,
            check=False,
            cwd=CODEX_WORKDIR,
            env={**os.environ, "CODEX_DISABLE_TELEMETRY": "1"},
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Codex catalog research 호출 시간이 초과되었습니다.")

    try:
        output_text = Path(output_path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        output_text = ""
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass

    if proc.returncode != 0:
        detail = (output_text or proc.stderr or proc.stdout or "").strip()
        raise HTTPException(status_code=502, detail=f"Codex catalog research 호출 실패: {detail or 'unknown error'}")
    if not output_text:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise HTTPException(status_code=502, detail=f"Codex catalog research 응답이 비어 있습니다. {detail}".strip())
    return _normalize_codex_result(_extract_json_payload(output_text))


@app.get("/health")
def health() -> dict[str, Literal["ok"] | bool | str]:
    return {"status": "ok", "auth": bool(SERVICE_TOKEN), "provider": PROVIDER}


@app.post("/lookup-hardware")
def lookup_hardware(payload: LookupHardwareRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _verify_auth(authorization)
    if PROVIDER == "anthropic":
        return _call_anthropic(_anthropic_prompt_from_args(payload))
    if PROVIDER == "codex":
        return _call_codex(_codex_prompt_from_args(payload))
    raise HTTPException(status_code=500, detail=f"지원하지 않는 provider입니다: {PROVIDER}")


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)

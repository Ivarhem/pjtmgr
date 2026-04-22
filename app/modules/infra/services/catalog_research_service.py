from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.models.hardware_spec import HardwareSpec
from app.modules.infra.schemas.hardware_interface import HardwareInterfaceCreate
from app.modules.infra.schemas.hardware_spec import HardwareSpecCreate
from app.modules.infra.schemas.product_catalog import ProductCatalogUpdate
from app.modules.infra.services.product_catalog_service import (
    create_interface,
    get_product,
    update_product,
    upsert_spec,
)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.getenv("CATALOG_RESEARCH_MODEL") or os.getenv("CLAUDE_MODEL") or "claude-sonnet-4-5"
UNCERTAIN_MARKERS = {"", "unknown", "n/a", "none", "null", "확인 필요", "미확인", "모름", "tbd", "na"}
VALID_CAPACITY_TYPES = {"fixed", "base", "max"}
VALID_CONFIDENCE = {"high", "medium", "low"}
SPEC_FIELDS = [
    "size_unit", "width_mm", "height_mm", "depth_mm", "weight_kg",
    "power_count", "power_type", "power_watt", "cpu_summary", "memory_summary",
    "throughput_summary", "os_firmware", "spec_url",
]
EOSL_FIELDS = ["eos_date", "eosl_date", "eosl_note"]

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


def _call_anthropic_json(prompt: str) -> dict:
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
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    raw = match.group(0) if match else cleaned
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BusinessRuleError(f"카탈로그 조사 응답 JSON 파싱 실패: {exc}", status_code=502)


def _clean_text(value, max_len: int | None = None):
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in UNCERTAIN_MARKERS:
        return None
    if max_len and len(text) > max_len:
        return text[:max_len]
    return text or None


def _clean_int(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip().lower()
    if text in UNCERTAIN_MARKERS:
        return None
    if text.endswith("u"):
        text = text[:-1]
    m = re.search(r"-?\d+", text)
    return int(m.group()) if m else None


def _clean_float(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if text in UNCERTAIN_MARKERS:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else None


def _clean_date(value):
    text = _clean_text(value, 32)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _merge_value(current, new, *, fill_only: bool):
    if new is None:
        return current
    if fill_only:
        if current is None:
            return new
        if isinstance(current, str) and not current.strip():
            return new
        return current
    return new


def _normalize_confidence(value) -> str:
    text = (_clean_text(value, 20) or "low").lower()
    return text if text in VALID_CONFIDENCE else "low"


def _normalize_capacity_type(value) -> str:
    text = (_clean_text(value, 10) or "fixed").lower()
    aliases = {"default": "base", "onboard": "fixed", "built-in": "fixed", "optional": "max"}
    text = aliases.get(text, text)
    return text if text in VALID_CAPACITY_TYPES else "fixed"


def _normalize_interfaces(items: list[dict]) -> tuple[list[dict], int]:
    merged: dict[tuple, dict] = {}
    skipped = 0
    for item in items or []:
        interface_type = _clean_text(item.get("interface_type"), 30)
        count = _clean_int(item.get("count"))
        if not interface_type or not count or count <= 0:
            skipped += 1
            continue
        row = {
            "interface_type": interface_type,
            "speed": _clean_text(item.get("speed"), 20),
            "count": count,
            "connector_type": _clean_text(item.get("connector_type"), 30),
            "capacity_type": _normalize_capacity_type(item.get("capacity_type")),
            "note": _clean_text(item.get("note"), 255),
        }
        key = (row["interface_type"], row["speed"], row["connector_type"], row["capacity_type"], row["note"])
        if key in merged:
            merged[key]["count"] += row["count"]
        else:
            merged[key] = row
    normalized = sorted(merged.values(), key=lambda x: (x["capacity_type"], x["interface_type"], x.get("speed") or "", x.get("connector_type") or ""))
    return normalized, skipped


def _count_non_null(mapping: dict, fields: list[str]) -> int:
    return sum(1 for field in fields if mapping.get(field) is not None)


def _classification_label(product) -> str:
    parts = []
    for attr in [
        getattr(product, "classification_level_1_name", None),
        getattr(product, "classification_level_2_name", None),
        getattr(product, "classification_level_3_name", None),
        getattr(product, "classification_level_4_name", None),
        getattr(product, "classification_level_5_name", None),
    ]:
        if attr:
            parts.append(attr)
    return " > ".join(parts) if parts else "unclassified"


def research_catalog_product(db: Session, product_id: int, current_user: User, fill_only: bool = True) -> dict:
    product = get_product(db, product_id)
    if product.product_type != "hardware":
        raise BusinessRuleError("현재 카탈로그 조사는 하드웨어 제품만 지원합니다.", status_code=409)

    existing_spec = db.scalar(select(HardwareSpec).where(HardwareSpec.product_id == product_id))
    payload = _call_anthropic_json(PROMPT_TEMPLATE.format(
        vendor=product.vendor,
        name=product.name,
        reference_url=product.reference_url or "none",
        classification=_classification_label(product),
        size_unit=getattr(existing_spec, "size_unit", None),
        power_count=getattr(existing_spec, "power_count", None),
        power_type=getattr(existing_spec, "power_type", None),
        power_watt=getattr(existing_spec, "power_watt", None),
    ))

    spec_data = payload.get("hardware_spec") or {}
    eosl_data = payload.get("eosl") or {}
    normalized_interfaces, invalid_interfaces = _normalize_interfaces(payload.get("interfaces") or [])
    confidence = _normalize_confidence(payload.get("confidence"))
    uncertain_fields = [
        _clean_text(item, 40) for item in (payload.get("uncertain_fields") or [])
        if _clean_text(item, 40)
    ]

    spec_payload = {
        "size_unit": _merge_value(existing_spec.size_unit if existing_spec else None, _clean_int(spec_data.get("size_unit")), fill_only=fill_only),
        "width_mm": _merge_value(existing_spec.width_mm if existing_spec else None, _clean_int(spec_data.get("width_mm")), fill_only=fill_only),
        "height_mm": _merge_value(existing_spec.height_mm if existing_spec else None, _clean_int(spec_data.get("height_mm")), fill_only=fill_only),
        "depth_mm": _merge_value(existing_spec.depth_mm if existing_spec else None, _clean_int(spec_data.get("depth_mm")), fill_only=fill_only),
        "weight_kg": _merge_value(existing_spec.weight_kg if existing_spec else None, _clean_float(spec_data.get("weight_kg")), fill_only=fill_only),
        "power_count": _merge_value(existing_spec.power_count if existing_spec else None, _clean_int(spec_data.get("power_count")), fill_only=fill_only),
        "power_type": _merge_value(existing_spec.power_type if existing_spec else None, _clean_text(spec_data.get("power_type"), 50), fill_only=fill_only),
        "power_watt": _merge_value(existing_spec.power_watt if existing_spec else None, _clean_int(spec_data.get("power_watt")), fill_only=fill_only),
        "cpu_summary": _merge_value(existing_spec.cpu_summary if existing_spec else None, _clean_text(spec_data.get("cpu_summary")), fill_only=fill_only),
        "memory_summary": _merge_value(existing_spec.memory_summary if existing_spec else None, _clean_text(spec_data.get("memory_summary")), fill_only=fill_only),
        "throughput_summary": _merge_value(existing_spec.throughput_summary if existing_spec else None, _clean_text(spec_data.get("throughput_summary")), fill_only=fill_only),
        "os_firmware": _merge_value(existing_spec.os_firmware if existing_spec else None, _clean_text(spec_data.get("os_firmware")), fill_only=fill_only),
        "spec_url": _merge_value(existing_spec.spec_url if existing_spec else None, _clean_text(spec_data.get("spec_url"), 500), fill_only=fill_only),
    }
    spec_candidates = _count_non_null({field: spec_payload.get(field) if spec_payload.get(field) != getattr(existing_spec, field, None) or not fill_only else _clean_text(spec_data.get(field), 500) if field in {"power_type", "cpu_summary", "memory_summary", "throughput_summary", "os_firmware", "spec_url"} else None for field in SPEC_FIELDS}, SPEC_FIELDS)
    spec_applied = sum(1 for field in SPEC_FIELDS if spec_payload.get(field) != getattr(existing_spec, field, None))
    upsert_spec(db, product_id, HardwareSpecCreate(**spec_payload), current_user)

    new_eos = _clean_date(eosl_data.get("eos_date"))
    new_eosl = _clean_date(eosl_data.get("eosl_date"))
    new_note = _clean_text(eosl_data.get("eosl_note"))
    new_source_url = _clean_text(eosl_data.get("source_url"), 500) or _clean_text(spec_data.get("spec_url"), 500)
    product_update = ProductCatalogUpdate(
        eos_date=_merge_value(product.eos_date, new_eos, fill_only=fill_only),
        eosl_date=_merge_value(product.eosl_date, new_eosl, fill_only=fill_only),
        eosl_note=_merge_value(product.eosl_note, new_note, fill_only=fill_only),
        reference_url=_merge_value(product.reference_url, _clean_text(spec_data.get("spec_url"), 500), fill_only=fill_only),
        source_name="catalog_research",
        source_url=new_source_url,
        source_confidence=confidence,
        verification_status="review_needed",
        last_verified_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    eosl_candidates = sum(1 for value in [new_eos, new_eosl, new_note] if value is not None)
    eosl_applied = sum(
        1 for old, new in [(product.eos_date, product_update.eos_date), (product.eosl_date, product_update.eosl_date), (product.eosl_note, product_update.eosl_note)]
        if new != old
    )
    update_product(db, product_id, product_update, current_user)

    existing_interfaces = list(db.scalars(select(HardwareInterface).where(HardwareInterface.product_id == product_id).order_by(HardwareInterface.id.asc())))
    interfaces_created = 0
    interfaces_skipped = invalid_interfaces
    should_create_interfaces = bool(normalized_interfaces) and (not fill_only or not existing_interfaces)
    if should_create_interfaces:
        if not fill_only and existing_interfaces:
            db.execute(delete(HardwareInterface).where(HardwareInterface.product_id == product_id))
            existing_interfaces = []
        for item in normalized_interfaces:
            create_interface(db, product_id, HardwareInterfaceCreate(**item), current_user)
            interfaces_created += 1
    elif normalized_interfaces and existing_interfaces:
        interfaces_skipped += len(normalized_interfaces)

    if spec_applied == 0 and eosl_applied == 0 and interfaces_created == 0 and not uncertain_fields:
        uncertain_fields.append("review_needed")

    audit.log(
        db,
        user_id=current_user.id,
        action="update",
        entity_type="product_catalog",
        entity_id=product_id,
        summary=f"카탈로그 조사 적용: {product.vendor} {product.name}",
        module="infra",
    )
    db.commit()

    return {
        "product_id": product_id,
        "vendor": product.vendor,
        "name": product.name,
        "mode": "fill_empty" if fill_only else "replace_all",
        "confidence": confidence,
        "spec_candidates": spec_candidates,
        "spec_applied": spec_applied,
        "eosl_candidates": eosl_candidates,
        "eosl_applied": eosl_applied,
        "interfaces_created": interfaces_created,
        "interface_candidates": len(normalized_interfaces),
        "interfaces_skipped": interfaces_skipped,
        "uncertain_fields": uncertain_fields,
        "eos_date": product_update.eos_date,
        "eosl_date": product_update.eosl_date,
        "spec_url": spec_payload.get("spec_url"),
        "message": "카탈로그 조사 결과를 반영했습니다.",
    }

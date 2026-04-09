from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.services.infra_exporter import export_partner
from app.core.file_validation import validate_xlsx
from app.modules.infra.services.infra_importer import (
    build_sample_template,
    import_inventory,
    import_portmaps,
    import_subnets,
    parse_inventory_sheet,
    parse_portmap_sheet,
    parse_subnet_sheet,
)
from app.modules.infra.services.product_catalog_importer import (
    build_eosl_template,
    build_model_template,
    build_software_template,
    build_spec_template,
    import_eosl,
    import_model,
    import_software,
    import_spec,
    parse_eosl_sheet,
    parse_model_sheet,
    parse_software_sheet,
    parse_spec_sheet,
)

router = APIRouter(prefix="/api/v1/infra-excel", tags=["infra-excel"])

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ── 파싱 함수 / Import 함수 매핑 ──

_DOMAIN_MAP = {
    "inventory": {"parse": parse_inventory_sheet, "import": import_inventory, "has_dup": True, "needs_partner": True},
    "subnet": {"parse": parse_subnet_sheet, "import": import_subnets, "has_dup": True, "needs_partner": True},
    "portmap": {"parse": parse_portmap_sheet, "import": import_portmaps, "has_dup": False, "needs_partner": True},
    "spec": {"parse": parse_spec_sheet, "import": import_spec, "has_dup": True, "needs_partner": False},
    "eosl": {"parse": parse_eosl_sheet, "import": import_eosl, "has_dup": True, "needs_partner": False},
    "software": {"parse": parse_software_sheet, "import": import_software, "has_dup": True, "needs_partner": False},
    "model": {"parse": parse_model_sheet, "import": import_model, "has_dup": True, "needs_partner": False},
}


def _build_catalog_lookup(db: Session) -> dict[tuple[str, str], ProductCatalog]:
    return {
        (product.vendor, product.name): product
        for product in db.scalars(select(ProductCatalog))
    }


def _is_same_value(left, right) -> bool:
    if left is None and right in ("", None):
        return True
    if right is None and left in ("", None):
        return True
    return left == right


def _enrich_catalog_preview_rows(
    db: Session,
    domain: str,
    preview_rows: list[dict],
    parsed_rows: list[dict],
    on_duplicate: str,
) -> list[dict]:
    if domain not in {"spec", "eosl", "software", "model"}:
        return preview_rows

    existing = _build_catalog_lookup(db)
    enriched_rows: list[dict] = []

    for index, row in enumerate(preview_rows):
        parsed = parsed_rows[index] if index < len(parsed_rows) else {}
        vendor = parsed.get("vendor") or row.get("vendor")
        name = parsed.get("name") or row.get("name")
        matched = existing.get((vendor, name)) if vendor and name else None

        status = "invalid"
        status_label = "검증오류"

        if row.get("errors"):
            status = "invalid"
            status_label = "검증오류"
        elif domain in {"spec", "software", "model"}:
            if matched is None:
                status = "new"
                status_label = "신규"
            elif on_duplicate == "overwrite":
                status = "update"
                status_label = "갱신예정"
            else:
                status = "skip_existing"
                status_label = "기존존재"
        elif domain == "eosl":
            if matched is None:
                status = "unmatched"
                status_label = "미매칭"
            else:
                changed = any(
                    not _is_same_value(getattr(matched, field), parsed.get(field))
                    for field in ("eos_date", "eosl_date", "eosl_note")
                    if parsed.get(field) is not None
                )
                if changed:
                    status = "update"
                    status_label = "갱신예정"
                else:
                    status = "unchanged"
                    status_label = "변경없음"

        enriched = dict(row)
        enriched["status"] = status
        enriched["status_label"] = status_label
        enriched["matched_product_id"] = matched.id if matched is not None else None
        enriched_rows.append(enriched)

    return enriched_rows


@router.post("/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    partner_id: int | None = Form(default=None),
    domain: str = Form(default="inventory"),
    on_duplicate: str = Form(default="skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """파일 업로드 + 파싱 결과 반환 (저장 안 함)."""
    validate_xlsx(file.filename, file.content_type)
    if domain not in _DOMAIN_MAP:
        raise ValidationError([f"지원하지 않는 도메인: {domain}"])
    content = await file.read()
    cfg = _DOMAIN_MAP[domain]
    if cfg["needs_partner"] and partner_id is None:
        raise ValidationError(["partner_id는 필수입니다."])
    if cfg["needs_partner"]:
        result = cfg["parse"](content, partner_id)
    else:
        result = cfg["parse"](content)
    preview_rows = _enrich_catalog_preview_rows(
        db,
        domain,
        result["preview_rows"],
        result["rows"],
        on_duplicate,
    )
    return {
        "valid": len(result["errors"]) == 0,
        "total": result["total"],
        "valid_count": result["valid_count"],
        "errors": result["errors"],
        "error_details": result["error_details"],
        "warnings": result["warnings"],
        "rows": preview_rows,
    }


@router.post("/import/confirm")
async def import_confirm(
    file: UploadFile = File(...),
    partner_id: int | None = Form(default=None),
    domain: str = Form(default="inventory"),
    on_duplicate: str = Form(default="skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """파싱 후 DB 저장."""
    validate_xlsx(file.filename, file.content_type)
    if domain not in _DOMAIN_MAP:
        raise ValidationError([f"지원하지 않는 도메인: {domain}"])

    content = await file.read()
    cfg = _DOMAIN_MAP[domain]

    # 재파싱
    if cfg["needs_partner"] and partner_id is None:
        raise ValidationError(["partner_id는 필수입니다."])
    if cfg["needs_partner"]:
        parsed = cfg["parse"](content, partner_id)
    else:
        parsed = cfg["parse"](content)
    if parsed["errors"]:
        raise ValidationError(parsed["errors"], details=parsed["error_details"])
    preview_rows = _enrich_catalog_preview_rows(
        db,
        domain,
        parsed["preview_rows"],
        parsed["rows"],
        on_duplicate,
    )
    preview_errors = [
        f"행 {row.get('row_num')}: {', '.join(row.get('errors', []))}"
        for row in preview_rows
        if row.get("errors")
    ]
    if preview_errors:
        raise ValidationError(preview_errors)

    # DB 저장
    import_fn = cfg["import"]
    if cfg["needs_partner"]:
        if cfg["has_dup"]:
            result = import_fn(db, partner_id, parsed["rows"], current_user, on_duplicate)
        else:
            result = import_fn(db, partner_id, parsed["rows"], current_user)
    else:
        if cfg["has_dup"]:
            result = import_fn(db, parsed["rows"], current_user, on_duplicate)
        else:
            result = import_fn(db, parsed["rows"], current_user)

    if result["errors"]:
        raise ValidationError(result["errors"], details=result["error_details"])

    return {
        "created": result["created"],
        "skipped": result["skipped"],
        "import_batch_id": result.get("import_batch_id"),
    }


@router.get("/export")
def export_partner_xlsx(
    partner_id: int = Query(...),
    period_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """업체 단위 Excel Export (자산/IP대역/포트맵). 기간 필터 옵션."""
    content = export_partner(db, partner_id, period_id)
    filename = f"partner_{partner_id}_export.xlsx"
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/template/{domain}")
def download_sample_template(
    domain: str,
    current_user: User = Depends(get_current_user),
) -> Response:
    """도메인별 Import 샘플 양식 다운로드."""
    if domain not in _DOMAIN_MAP:
        raise ValidationError([f"지원하지 않는 도메인: {domain}"])
    if domain == "spec":
        content = build_spec_template()
    elif domain == "eosl":
        content = build_eosl_template()
    elif domain == "software":
        content = build_software_template()
    elif domain == "model":
        content = build_model_template()
    else:
        content = build_sample_template(domain)
    filename = f"import_template_{domain}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

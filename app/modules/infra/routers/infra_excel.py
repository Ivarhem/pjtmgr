from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.modules.infra.services.infra_exporter import export_customer
from app.modules.infra.services.infra_importer import (
    build_sample_template,
    import_inventory,
    import_portmaps,
    import_subnets,
    parse_inventory_sheet,
    parse_portmap_sheet,
    parse_subnet_sheet,
    validate_xlsx,
)
from app.modules.infra.services.product_catalog_importer import (
    build_eosl_template,
    build_spec_template,
    import_eosl,
    import_spec,
    parse_eosl_sheet,
    parse_spec_sheet,
)

router = APIRouter(prefix="/api/v1/infra-excel", tags=["infra-excel"])

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ── 파싱 함수 / Import 함수 매핑 ──

_DOMAIN_MAP = {
    "inventory": {"parse": parse_inventory_sheet, "import": import_inventory, "has_dup": True, "needs_customer": True},
    "subnet": {"parse": parse_subnet_sheet, "import": import_subnets, "has_dup": True, "needs_customer": True},
    "portmap": {"parse": parse_portmap_sheet, "import": import_portmaps, "has_dup": False, "needs_customer": True},
    "spec": {"parse": parse_spec_sheet, "import": import_spec, "has_dup": True, "needs_customer": False},
    "eosl": {"parse": parse_eosl_sheet, "import": import_eosl, "has_dup": True, "needs_customer": False},
}


@router.post("/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    customer_id: int = Form(...),
    domain: str = Form(default="inventory"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """파일 업로드 + 파싱 결과 반환 (저장 안 함)."""
    validate_xlsx(file.filename, file.content_type)
    if domain not in _DOMAIN_MAP:
        raise ValidationError([f"지원하지 않는 도메인: {domain}"])
    content = await file.read()
    cfg = _DOMAIN_MAP[domain]
    if cfg["needs_customer"]:
        result = cfg["parse"](content, customer_id)
    else:
        result = cfg["parse"](content)
    return {
        "valid": len(result["errors"]) == 0,
        "total": result["total"],
        "valid_count": result["valid_count"],
        "errors": result["errors"],
        "error_details": result["error_details"],
        "warnings": result["warnings"],
        "rows": result["preview_rows"],
    }


@router.post("/import/confirm")
async def import_confirm(
    file: UploadFile = File(...),
    customer_id: int = Form(...),
    domain: str = Form(default="inventory"),
    on_duplicate: str = Form(default="skip"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """파싱 후 DB 저장."""
    validate_xlsx(file.filename, file.content_type)
    if domain not in _DOMAIN_MAP:
        raise ValidationError([f"지원하지 않는 도메인: {domain}"])

    content = await file.read()
    cfg = _DOMAIN_MAP[domain]

    # 재파싱
    if cfg["needs_customer"]:
        parsed = cfg["parse"](content, customer_id)
    else:
        parsed = cfg["parse"](content)
    if parsed["errors"]:
        raise ValidationError(parsed["errors"], details=parsed["error_details"])

    # DB 저장
    import_fn = cfg["import"]
    if cfg["needs_customer"]:
        if cfg["has_dup"]:
            result = import_fn(db, customer_id, parsed["rows"], current_user, on_duplicate)
        else:
            result = import_fn(db, customer_id, parsed["rows"], current_user)
    else:
        if cfg["has_dup"]:
            result = import_fn(db, parsed["rows"], current_user, on_duplicate)
        else:
            result = import_fn(db, parsed["rows"], current_user)

    if result["errors"]:
        raise ValidationError(result["errors"], details=result["error_details"])

    return {"created": result["created"], "skipped": result["skipped"]}


@router.get("/export")
def export_customer_xlsx(
    customer_id: int = Query(...),
    period_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """고객사 단위 Excel Export (자산/IP대역/포트맵). 기간 필터 옵션."""
    content = export_customer(db, customer_id, period_id)
    filename = f"customer_{customer_id}_export.xlsx"
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/template/{domain}")
def download_sample_template(
    domain: str,
    current_user=Depends(get_current_user),
) -> Response:
    """도메인별 Import 샘플 양식 다운로드."""
    if domain not in _DOMAIN_MAP:
        raise ValidationError([f"지원하지 않는 도메인: {domain}"])
    if domain == "spec":
        content = build_spec_template()
    elif domain == "eosl":
        content = build_eosl_template()
    else:
        content = build_sample_template(domain)
    filename = f"import_template_{domain}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

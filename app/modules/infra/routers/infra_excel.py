from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import ValidationError
from app.modules.infra.services.infra_exporter import export_project
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

router = APIRouter(prefix="/api/v1/infra-excel", tags=["infra-excel"])

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ── 파싱 함수 / Import 함수 매핑 ──

_DOMAIN_MAP = {
    "inventory": {"parse": parse_inventory_sheet, "import": import_inventory, "has_dup": True},
    "subnet": {"parse": parse_subnet_sheet, "import": import_subnets, "has_dup": True},
    "portmap": {"parse": parse_portmap_sheet, "import": import_portmaps, "has_dup": False},
}


@router.post("/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    domain: str = Form(default="inventory"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    """파일 업로드 + 파싱 결과 반환 (저장 안 함)."""
    validate_xlsx(file.filename, file.content_type)
    if domain not in _DOMAIN_MAP:
        raise ValidationError([f"지원하지 않는 도메인: {domain}"])
    content = await file.read()
    result = _DOMAIN_MAP[domain]["parse"](content, project_id)
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
    project_id: int = Form(...),
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
    parsed = cfg["parse"](content, project_id)
    if parsed["errors"]:
        raise ValidationError(parsed["errors"], details=parsed["error_details"])

    # DB 저장
    import_fn = cfg["import"]
    if cfg["has_dup"]:
        result = import_fn(db, project_id, parsed["rows"], current_user, on_duplicate)
    else:
        result = import_fn(db, project_id, parsed["rows"], current_user)

    if result["errors"]:
        raise ValidationError(result["errors"], details=result["error_details"])

    return {"created": result["created"], "skipped": result["skipped"]}


@router.get("/export/{project_id}")
def export_project_xlsx(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    """프로젝트 단위 Excel Export (자산/IP대역/포트맵)."""
    content = export_project(db, project_id)
    filename = f"project_{project_id}_export.xlsx"
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
    content = build_sample_template(domain)
    filename = f"import_template_{domain}.xlsx"
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

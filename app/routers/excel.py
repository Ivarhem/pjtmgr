from fastapi import APIRouter, Depends, File, UploadFile, Form, Request
from fastapi.responses import Response, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import require_admin
from app.models.user import User
from app.services.exporter import build_template, build_template_contracts, build_template_forecast, build_template_actuals
from app.services.importer import parse_and_validate, import_data, import_forecast_sheet, import_actuals_sheet, validate_xlsx
from app.services import contract as contract_svc
from app.services.contract_type_config import list_contract_types as _list_contract_types
from app.exceptions import ValidationError

router = APIRouter(prefix="/api/v1/excel", tags=["excel"])
templates = Jinja2Templates(directory="app/templates")

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/template")
def download_template(db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> Response:
    codes = [dt.code for dt in _list_contract_types(db)]
    content = build_template(contract_type_codes=codes)
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": "attachment; filename=import_template.xlsx"},
    )


@router.get("/template/contracts")
def download_contracts_template(db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> Response:
    """영업기회 전용 블랭크 템플릿"""
    codes = [dt.code for dt in _list_contract_types(db)]
    content = build_template_contracts(contract_type_codes=codes)
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": "attachment; filename=contracts_template.xlsx"},
    )


@router.get("/template/forecast")
def download_forecast_template(db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> Response:
    """월별계획 템플릿 — 기존 등록 영업기회 목록 포함"""
    periods_data = contract_svc.list_periods_for_template(db)
    content = build_template_forecast(periods_data)
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": "attachment; filename=forecast_template.xlsx"},
    )


@router.get("/template/transaction-lines")
def download_transaction_lines_template(db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> Response:
    """실적 템플릿 — 기존 등록 영업기회 목록 포함"""
    periods_data = contract_svc.list_periods_for_template(db)
    content = build_template_actuals(periods_data)
    return Response(
        content=content,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": "attachment; filename=transaction_lines_template.xlsx"},
    )


@router.post("/import/forecast")
async def import_forecast(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """월별계획 시트 단독 Import (관리자 전용)"""
    validate_xlsx(file.filename, file.content_type)
    content = await file.read()
    result = import_forecast_sheet(db, content)
    if result["errors"]:
        raise ValidationError(result["errors"])
    return {"saved": result["saved"]}


@router.post("/import/transaction-lines")
async def import_transaction_lines(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """실적 시트 단독 Import (관리자 전용)"""
    validate_xlsx(file.filename, file.content_type)
    content = await file.read()
    result = import_actuals_sheet(db, content)
    if result["errors"]:
        raise ValidationError(result["errors"])
    return {"saved": result["saved"]}


@router.post("/validate")
async def validate_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """파싱 + 유효성 검사만 수행 (저장 안 함) → 미리보기용"""
    validate_xlsx(file.filename, file.content_type)
    content = await file.read()
    result = parse_and_validate(content, db=db)
    return {
        "errors": result["errors"],
        "counts": result.get("counts", {}),
        "valid": len(result["errors"]) == 0,
    }


@router.post("/import")
async def do_import(
    file: UploadFile = File(...),
    on_duplicate: str = Form(default="overwrite"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """실제 DB 저장 (관리자 전용)"""
    validate_xlsx(file.filename, file.content_type)
    content = await file.read()
    result = import_data(db, content, on_duplicate=on_duplicate)
    if result["errors"]:
        raise ValidationError(result["errors"])
    return {
        "created": result["created"],
        "skipped": result["skipped"],
        "new_users": result["new_users"],
    }

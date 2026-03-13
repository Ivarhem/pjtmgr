from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.contract_type_config import ContractTypeRead, ContractTypeCreate, ContractTypeUpdate
from app.services import contract_type_config as svc

router = APIRouter(prefix="/api/v1/contract-types", tags=["contract-types"])


def _to_read(dt) -> ContractTypeRead:
    return ContractTypeRead(
        code=dt.code, label=dt.label, sort_order=dt.sort_order, is_active=dt.is_active,
        default_gp_pct=dt.default_gp_pct,
        default_inspection_day=dt.default_inspection_day,
        default_invoice_month_offset=dt.default_invoice_month_offset,
        default_invoice_day_type=dt.default_invoice_day_type,
        default_invoice_day=dt.default_invoice_day,
        default_invoice_holiday_adjust=dt.default_invoice_holiday_adjust,
    )


@router.get("", response_model=list[ContractTypeRead])
def list_contract_types(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return [_to_read(dt) for dt in svc.list_contract_types(db, active_only=active_only)]


@router.post("", response_model=ContractTypeRead, status_code=201)
def create_contract_type(
    data: ContractTypeCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    dt = svc.create_contract_type(db, data.code, data.label, data.sort_order, defaults=data.model_dump(exclude={"code", "label", "sort_order"}))
    return _to_read(dt)


@router.patch("/{code}", response_model=ContractTypeRead)
def update_contract_type(
    code: str,
    data: ContractTypeUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    dt = svc.update_contract_type(db, code, updates=data.model_dump(exclude_unset=True))
    return _to_read(dt)


@router.delete("/{code}", status_code=204)
def delete_contract_type(
    code: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    svc.delete_contract_type(db, code)

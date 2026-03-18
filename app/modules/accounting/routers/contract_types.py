from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth.dependencies import get_current_user, require_admin
from app.modules.common.models.user import User
from app.modules.accounting.schemas.contract_type_config import ContractTypeRead, ContractTypeCreate, ContractTypeUpdate
from app.modules.accounting.services import contract_type_config as svc

router = APIRouter(prefix="/api/v1/contract-types", tags=["contract-types"])


@router.get("", response_model=list[ContractTypeRead])
def list_contract_types(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[ContractTypeRead]:
    return svc.list_contract_types(db, active_only=active_only)


@router.post("", response_model=ContractTypeRead, status_code=201)
def create_contract_type(
    data: ContractTypeCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ContractTypeRead:
    return svc.create_contract_type(db, data.code, data.label, data.sort_order, defaults=data.model_dump(exclude={"code", "label", "sort_order"}))


@router.patch("/{code}", response_model=ContractTypeRead)
def update_contract_type(
    code: str,
    data: ContractTypeUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ContractTypeRead:
    return svc.update_contract_type(db, code, updates=data.model_dump(exclude_unset=True))


@router.delete("/{code}", status_code=204)
def delete_contract_type(
    code: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_contract_type(db, code)

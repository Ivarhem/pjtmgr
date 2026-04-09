from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.accounting.schemas.contract_contact import ContractContactCreate, ContractContactUpdate
from app.modules.accounting.services import contract_contact as svc
from app.core.auth.dependencies import get_current_user, require_module_access
from app.modules.common.models.user import User
from app.core.auth.authorization import check_contract_access, check_period_access

router = APIRouter(prefix="/api/v1", tags=["contract-contacts"])


@router.get("/contracts/{contract_id}/contacts")
def list_contract_contacts(contract_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    check_contract_access(db, contract_id, current_user)
    return svc.list_by_contract(db, contract_id)


@router.post("/contracts/{contract_id}/contacts", status_code=201, dependencies=[require_module_access("accounting", "full")])
def create_contract_contact_compat(contract_id: int, data: ContractContactCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    """Contract의 최신 Period에 담당자 등록 (하위 호환)."""
    check_contract_access(db, contract_id, current_user)
    return svc.create_contract_contact_for_contract(db, contract_id, data)


@router.get("/contract-periods/{period_id}/contacts")
def list_period_contacts(period_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    check_period_access(db, period_id, current_user)
    return svc.list_by_period(db, period_id)


@router.post("/contract-periods/{period_id}/contacts", status_code=201, dependencies=[require_module_access("accounting", "full")])
def create_period_contact(period_id: int, data: ContractContactCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    check_period_access(db, period_id, current_user)
    return svc.create_contract_contact(db, period_id, data)


@router.get("/partners/{partner_id}/contract-contacts")
def list_partner_contract_contacts(partner_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    return svc.list_by_partner(db, partner_id, current_user=current_user)


@router.get("/partners/{partner_id}/contract-contacts-pivoted")
def list_partner_contract_contacts_pivoted(partner_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    return svc.list_by_partner_pivoted(db, partner_id, current_user=current_user)


@router.patch("/contract-contacts/{contact_id}", dependencies=[require_module_access("accounting", "full")])
def update_contract_contact(contact_id: int, data: ContractContactUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return svc.update_contract_contact(db, contact_id, data, current_user=current_user)


@router.delete("/contract-contacts/{contact_id}", status_code=204, dependencies=[require_module_access("accounting", "full")])
def delete_contract_contact(contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    svc.delete_contract_contact(db, contact_id, current_user=current_user)

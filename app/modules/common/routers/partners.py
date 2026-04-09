from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.common.schemas.partner import PartnerCreate, PartnerUpdate, PartnerRead, PartnerListRead
from app.modules.common.schemas.partner_contact import PartnerContactCreate, PartnerContactUpdate
from app.modules.common.services import partner as svc
from app.core.auth.dependencies import get_current_user, require_admin
from app.modules.common.models.user import User

router = APIRouter(prefix="/api/v1/partners", tags=["partners"])


@router.get("", response_model=list[PartnerListRead])
def list_partners(
    my_only: bool = False,
    partner_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PartnerListRead]:
    return svc.list_partners(db, current_user=current_user, my_only=my_only, partner_type=partner_type)


@router.post("", response_model=PartnerRead, status_code=201)
def create_partner(data: PartnerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PartnerRead:
    return svc.create_partner(db, data)


@router.get("/{partner_id}/contracts")
def list_partner_contracts(partner_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return svc.list_related_contracts(db, partner_id, current_user=current_user)


@router.get("/{partner_id}/financials")
def list_partner_financials(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.list_partner_financials(db, partner_id, current_user=current_user)


@router.get("/{partner_id}/receipts")
def list_partner_receipts(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.list_partner_receipts(db, partner_id, current_user=current_user)


@router.delete("/{partner_id}", status_code=204)
def delete_partner(
    partner_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_partner(db, partner_id)


@router.patch("/{partner_id}", response_model=PartnerRead)
def update_partner(partner_id: int, data: PartnerUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PartnerRead:
    return svc.update_partner(db, partner_id, data)


# ── 담당자 (PartnerContact) ─────────────────────────────────


@router.get("/{partner_id}/contacts")
def list_contacts(partner_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    return svc.get_contacts(db, partner_id)


@router.post("/{partner_id}/contacts", status_code=201)
def create_contact(partner_id: int, data: PartnerContactCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return svc.create_contact(db, partner_id, data)


@router.patch("/contacts/{contact_id}")
def update_contact(contact_id: int, data: PartnerContactUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return svc.update_contact(db, contact_id, data)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)) -> None:
    svc.delete_contact(db, contact_id)

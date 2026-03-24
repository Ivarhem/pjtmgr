from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.partner_contact import PartnerContact
from app.modules.infra.models.period_partner import PeriodPartner
from app.modules.infra.models.period_partner_contact import PeriodPartnerContact
from app.modules.infra.schemas.period_partner_contact import (
    PeriodPartnerContactCreate,
    PeriodPartnerContactUpdate,
)


def list_by_period_partner(
    db: Session, period_partner_id: int
) -> list[dict]:
    links = list(
        db.scalars(
            select(PeriodPartnerContact)
            .where(PeriodPartnerContact.period_partner_id == period_partner_id)
            .order_by(PeriodPartnerContact.id.asc())
        )
    )
    return _enrich(db, links)


def list_by_period(db: Session, contract_period_id: int) -> list[dict]:
    """기간의 모든 업체에 소속된 담당자를 한 번에 조회."""
    pp_ids = list(
        db.scalars(
            select(PeriodPartner.id).where(
                PeriodPartner.contract_period_id == contract_period_id
            )
        )
    )
    if not pp_ids:
        return []
    links = list(
        db.scalars(
            select(PeriodPartnerContact)
            .where(PeriodPartnerContact.period_partner_id.in_(pp_ids))
            .order_by(PeriodPartnerContact.period_partner_id, PeriodPartnerContact.id)
        )
    )
    return _enrich(db, links)


def create_period_partner_contact(
    db: Session, payload: PeriodPartnerContactCreate, current_user
) -> PeriodPartnerContact:
    _require_edit(current_user)
    _ensure_period_partner(db, payload.period_partner_id)
    _ensure_contact(db, payload.contact_id)
    _ensure_unique(
        db, payload.period_partner_id, payload.contact_id, payload.project_role
    )

    ppc = PeriodPartnerContact(**payload.model_dump())
    db.add(ppc)
    db.commit()
    db.refresh(ppc)
    return ppc


def update_period_partner_contact(
    db: Session, link_id: int, payload: PeriodPartnerContactUpdate, current_user
) -> PeriodPartnerContact:
    _require_edit(current_user)
    ppc = _get(db, link_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ppc, field, value)
    db.commit()
    db.refresh(ppc)
    return ppc


def delete_period_partner_contact(db: Session, link_id: int, current_user) -> None:
    _require_edit(current_user)
    ppc = _get(db, link_id)
    db.delete(ppc)
    db.commit()


# -- Private --


def _get(db: Session, link_id: int) -> PeriodPartnerContact:
    ppc = db.get(PeriodPartnerContact, link_id)
    if ppc is None:
        raise NotFoundError("Period-Partner-Contact link not found")
    return ppc


def _ensure_period_partner(db: Session, period_partner_id: int) -> None:
    if db.get(PeriodPartner, period_partner_id) is None:
        raise NotFoundError("Period-Partner link not found")


def _ensure_contact(db: Session, contact_id: int) -> None:
    if db.get(PartnerContact, contact_id) is None:
        raise NotFoundError("Contact not found")


def _ensure_unique(
    db: Session, period_partner_id: int, contact_id: int, project_role: str
) -> None:
    existing = db.scalar(
        select(PeriodPartnerContact).where(
            PeriodPartnerContact.period_partner_id == period_partner_id,
            PeriodPartnerContact.contact_id == contact_id,
            PeriodPartnerContact.project_role == project_role,
        )
    )
    if existing:
        raise DuplicateError(
            "This contact-role is already linked to the period partner"
        )


def _require_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _enrich(db: Session, links: list[PeriodPartnerContact]) -> list[dict]:
    if not links:
        return []
    contact_ids = {l.contact_id for l in links}
    contacts = {
        c.id: c
        for c in db.scalars(
            select(PartnerContact).where(PartnerContact.id.in_(contact_ids))
        )
    }
    result = []
    for l in links:
        d = {
            c.key: getattr(l, c.key)
            for c in PeriodPartnerContact.__table__.columns
        }
        d["created_at"] = l.created_at
        d["updated_at"] = l.updated_at
        ct = contacts.get(l.contact_id)
        d["contact_name"] = ct.name if ct else None
        d["contact_phone"] = ct.phone if ct else None
        d["contact_email"] = ct.email if ct else None
        result.append(d)
    return result

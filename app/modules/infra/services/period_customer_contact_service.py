from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.customer_contact import CustomerContact
from app.modules.infra.models.period_customer import PeriodCustomer
from app.modules.infra.models.period_customer_contact import PeriodCustomerContact
from app.modules.infra.schemas.period_customer_contact import (
    PeriodCustomerContactCreate,
    PeriodCustomerContactUpdate,
)


def list_by_period_customer(
    db: Session, period_customer_id: int
) -> list[dict]:
    links = list(
        db.scalars(
            select(PeriodCustomerContact)
            .where(PeriodCustomerContact.period_customer_id == period_customer_id)
            .order_by(PeriodCustomerContact.id.asc())
        )
    )
    return _enrich(db, links)


def list_by_period(db: Session, contract_period_id: int) -> list[dict]:
    """기간의 모든 업체에 소속된 담당자를 한 번에 조회."""
    pc_ids = list(
        db.scalars(
            select(PeriodCustomer.id).where(
                PeriodCustomer.contract_period_id == contract_period_id
            )
        )
    )
    if not pc_ids:
        return []
    links = list(
        db.scalars(
            select(PeriodCustomerContact)
            .where(PeriodCustomerContact.period_customer_id.in_(pc_ids))
            .order_by(PeriodCustomerContact.period_customer_id, PeriodCustomerContact.id)
        )
    )
    return _enrich(db, links)


def create_period_customer_contact(
    db: Session, payload: PeriodCustomerContactCreate, current_user
) -> PeriodCustomerContact:
    _require_edit(current_user)
    _ensure_period_customer(db, payload.period_customer_id)
    _ensure_contact(db, payload.contact_id)
    _ensure_unique(
        db, payload.period_customer_id, payload.contact_id, payload.project_role
    )

    pcc = PeriodCustomerContact(**payload.model_dump())
    db.add(pcc)
    db.commit()
    db.refresh(pcc)
    return pcc


def update_period_customer_contact(
    db: Session, link_id: int, payload: PeriodCustomerContactUpdate, current_user
) -> PeriodCustomerContact:
    _require_edit(current_user)
    pcc = _get(db, link_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pcc, field, value)
    db.commit()
    db.refresh(pcc)
    return pcc


def delete_period_customer_contact(db: Session, link_id: int, current_user) -> None:
    _require_edit(current_user)
    pcc = _get(db, link_id)
    db.delete(pcc)
    db.commit()


# -- Private --


def _get(db: Session, link_id: int) -> PeriodCustomerContact:
    pcc = db.get(PeriodCustomerContact, link_id)
    if pcc is None:
        raise NotFoundError("Period-Customer-Contact link not found")
    return pcc


def _ensure_period_customer(db: Session, period_customer_id: int) -> None:
    if db.get(PeriodCustomer, period_customer_id) is None:
        raise NotFoundError("Period-Customer link not found")


def _ensure_contact(db: Session, contact_id: int) -> None:
    if db.get(CustomerContact, contact_id) is None:
        raise NotFoundError("Contact not found")


def _ensure_unique(
    db: Session, period_customer_id: int, contact_id: int, project_role: str
) -> None:
    existing = db.scalar(
        select(PeriodCustomerContact).where(
            PeriodCustomerContact.period_customer_id == period_customer_id,
            PeriodCustomerContact.contact_id == contact_id,
            PeriodCustomerContact.project_role == project_role,
        )
    )
    if existing:
        raise DuplicateError(
            "This contact-role is already linked to the period customer"
        )


def _require_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _enrich(db: Session, links: list[PeriodCustomerContact]) -> list[dict]:
    if not links:
        return []
    contact_ids = {l.contact_id for l in links}
    contacts = {
        c.id: c
        for c in db.scalars(
            select(CustomerContact).where(CustomerContact.id.in_(contact_ids))
        )
    }
    result = []
    for l in links:
        d = {
            c.key: getattr(l, c.key)
            for c in PeriodCustomerContact.__table__.columns
        }
        d["created_at"] = l.created_at
        d["updated_at"] = l.updated_at
        ct = contacts.get(l.contact_id)
        d["contact_name"] = ct.name if ct else None
        d["contact_phone"] = ct.phone if ct else None
        d["contact_email"] = ct.email if ct else None
        result.append(d)
    return result

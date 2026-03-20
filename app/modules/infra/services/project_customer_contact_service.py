from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.customer_contact import CustomerContact
from app.modules.infra.models.project_customer import ProjectCustomer
from app.modules.infra.models.project_customer_contact import ProjectCustomerContact
from app.modules.infra.schemas.project_customer_contact import (
    ProjectCustomerContactCreate,
    ProjectCustomerContactUpdate,
)


def list_by_project_customer(
    db: Session, project_customer_id: int
) -> list[dict]:
    links = list(
        db.scalars(
            select(ProjectCustomerContact)
            .where(ProjectCustomerContact.project_customer_id == project_customer_id)
            .order_by(ProjectCustomerContact.id.asc())
        )
    )
    return _enrich(db, links)


def list_by_project(db: Session, project_id: int) -> list[dict]:
    """프로젝트의 모든 업체에 소속된 담당자를 한 번에 조회."""
    pc_ids = list(
        db.scalars(
            select(ProjectCustomer.id).where(
                ProjectCustomer.project_id == project_id
            )
        )
    )
    if not pc_ids:
        return []
    links = list(
        db.scalars(
            select(ProjectCustomerContact)
            .where(ProjectCustomerContact.project_customer_id.in_(pc_ids))
            .order_by(ProjectCustomerContact.project_customer_id, ProjectCustomerContact.id)
        )
    )
    return _enrich(db, links)


def create(
    db: Session, payload: ProjectCustomerContactCreate, current_user
) -> ProjectCustomerContact:
    _require_edit(current_user)
    _ensure_project_customer(db, payload.project_customer_id)
    _ensure_contact(db, payload.contact_id)
    _ensure_unique(
        db, payload.project_customer_id, payload.contact_id, payload.project_role
    )

    pcc = ProjectCustomerContact(**payload.model_dump())
    db.add(pcc)
    db.commit()
    db.refresh(pcc)
    return pcc


def update(
    db: Session, link_id: int, payload: ProjectCustomerContactUpdate, current_user
) -> ProjectCustomerContact:
    _require_edit(current_user)
    pcc = _get(db, link_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pcc, field, value)
    db.commit()
    db.refresh(pcc)
    return pcc


def delete(db: Session, link_id: int, current_user) -> None:
    _require_edit(current_user)
    pcc = _get(db, link_id)
    db.delete(pcc)
    db.commit()


# ── Private ──


def _get(db: Session, link_id: int) -> ProjectCustomerContact:
    pcc = db.get(ProjectCustomerContact, link_id)
    if pcc is None:
        raise NotFoundError("Project-Customer-Contact link not found")
    return pcc


def _ensure_project_customer(db: Session, project_customer_id: int) -> None:
    if db.get(ProjectCustomer, project_customer_id) is None:
        raise NotFoundError("Project-Customer link not found")


def _ensure_contact(db: Session, contact_id: int) -> None:
    if db.get(CustomerContact, contact_id) is None:
        raise NotFoundError("Contact not found")


def _ensure_unique(
    db: Session, project_customer_id: int, contact_id: int, project_role: str
) -> None:
    existing = db.scalar(
        select(ProjectCustomerContact).where(
            ProjectCustomerContact.project_customer_id == project_customer_id,
            ProjectCustomerContact.contact_id == contact_id,
            ProjectCustomerContact.project_role == project_role,
        )
    )
    if existing:
        raise DuplicateError(
            "This contact-role is already linked to the project customer"
        )


def _require_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _enrich(db: Session, links: list[ProjectCustomerContact]) -> list[dict]:
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
            for c in ProjectCustomerContact.__table__.columns
        }
        d["created_at"] = l.created_at
        d["updated_at"] = l.updated_at
        ct = contacts.get(l.contact_id)
        d["contact_name"] = ct.name if ct else None
        d["contact_phone"] = ct.phone if ct else None
        d["contact_email"] = ct.email if ct else None
        result.append(d)
    return result

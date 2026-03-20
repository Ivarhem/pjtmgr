from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.customer import Customer
from app.modules.infra.models.project import Project
from app.modules.infra.models.project_customer import ProjectCustomer
from app.modules.infra.schemas.project_customer import (
    ProjectCustomerCreate,
    ProjectCustomerUpdate,
)


def list_by_project(db: Session, project_id: int) -> list[dict]:
    links = list(
        db.scalars(
            select(ProjectCustomer)
            .where(ProjectCustomer.project_id == project_id)
            .order_by(ProjectCustomer.id.asc())
        )
    )
    return _enrich(db, links)


def create_project_customer(
    db: Session, payload: ProjectCustomerCreate, current_user
) -> ProjectCustomer:
    _require_edit(current_user)
    _ensure_project(db, payload.project_id)
    _ensure_customer(db, payload.customer_id)
    _ensure_unique(db, payload.project_id, payload.customer_id, payload.role)

    pc = ProjectCustomer(**payload.model_dump())
    db.add(pc)
    db.commit()
    db.refresh(pc)
    return pc


def update_project_customer(
    db: Session, link_id: int, payload: ProjectCustomerUpdate, current_user
) -> ProjectCustomer:
    _require_edit(current_user)
    pc = _get(db, link_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pc, field, value)
    db.commit()
    db.refresh(pc)
    return pc


def delete_project_customer(db: Session, link_id: int, current_user) -> None:
    _require_edit(current_user)
    pc = _get(db, link_id)
    db.delete(pc)
    db.commit()


# ── Private ──


def _get(db: Session, link_id: int) -> ProjectCustomer:
    pc = db.get(ProjectCustomer, link_id)
    if pc is None:
        raise NotFoundError("Project-Customer link not found")
    return pc


def _ensure_project(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_customer(db: Session, customer_id: int) -> None:
    if db.get(Customer, customer_id) is None:
        raise NotFoundError("Customer not found")


def _ensure_unique(
    db: Session, project_id: int, customer_id: int, role: str
) -> None:
    existing = db.scalar(
        select(ProjectCustomer).where(
            ProjectCustomer.project_id == project_id,
            ProjectCustomer.customer_id == customer_id,
            ProjectCustomer.role == role,
        )
    )
    if existing:
        raise DuplicateError("This customer-role is already linked to the project")


def _require_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _enrich(db: Session, links: list[ProjectCustomer]) -> list[dict]:
    if not links:
        return []
    customer_ids = {l.customer_id for l in links}
    customers = {
        c.id: c
        for c in db.scalars(select(Customer).where(Customer.id.in_(customer_ids)))
    }
    result = []
    for l in links:
        d = {c.key: getattr(l, c.key) for c in ProjectCustomer.__table__.columns}
        d["created_at"] = l.created_at
        d["updated_at"] = l.updated_at
        cust = customers.get(l.customer_id)
        d["customer_name"] = cust.name if cust else None
        d["business_no"] = cust.business_no if cust else None
        result.append(d)
    return result

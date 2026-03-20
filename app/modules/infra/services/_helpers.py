"""Shared helpers for infra services (customer-centric)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.common.models.customer import Customer
from app.modules.infra.models.project_asset import ProjectAsset


def get_project_asset_ids(db: Session, project_id: int) -> set[int]:
    """Return asset IDs linked to a project via ProjectAsset."""
    return set(
        db.scalars(
            select(ProjectAsset.asset_id).where(
                ProjectAsset.project_id == project_id
            )
        )
    )


def ensure_customer_exists(db: Session, customer_id: int) -> None:
    """Raise NotFoundError if customer does not exist."""
    if db.get(Customer, customer_id) is None:
        raise NotFoundError("Customer not found")

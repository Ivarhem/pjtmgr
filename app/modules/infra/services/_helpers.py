"""Shared helpers for infra services (customer-centric)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.common.models.customer import Customer
from app.modules.infra.models.period_asset import PeriodAsset


def get_period_asset_ids(db: Session, contract_period_id: int) -> set[int]:
    """Return asset IDs linked to a contract period via PeriodAsset."""
    return set(
        db.scalars(
            select(PeriodAsset.asset_id).where(
                PeriodAsset.contract_period_id == contract_period_id
            )
        )
    )


def ensure_customer_exists(db: Session, customer_id: int) -> None:
    """Raise NotFoundError if customer does not exist."""
    if db.get(Customer, customer_id) is None:
        raise NotFoundError("Customer not found")

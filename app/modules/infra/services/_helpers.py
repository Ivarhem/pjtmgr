"""Shared helpers for infra services (partner-centric)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.common.models.partner import Partner
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


def ensure_partner_exists(db: Session, partner_id: int) -> None:
    """Raise NotFoundError if partner does not exist."""
    if db.get(Partner, partner_id) is None:
        raise NotFoundError("Partner not found")

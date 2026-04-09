from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.period_asset import PeriodAsset
from app.modules.infra.schemas.period_asset import PeriodAssetCreate, PeriodAssetUpdate


def list_by_period(db: Session, contract_period_id: int) -> list[dict]:
    links = list(
        db.scalars(
            select(PeriodAsset)
            .where(PeriodAsset.contract_period_id == contract_period_id)
            .order_by(PeriodAsset.id.asc())
        )
    )
    return _enrich(db, links)


def list_by_asset(db: Session, asset_id: int) -> list[dict]:
    links = list(
        db.scalars(
            select(PeriodAsset)
            .where(PeriodAsset.asset_id == asset_id)
            .order_by(PeriodAsset.id.asc())
        )
    )
    return _enrich(db, links)


def create_period_asset(db: Session, payload: PeriodAssetCreate, current_user) -> PeriodAsset:
    _require_edit(current_user)
    _ensure_period(db, payload.contract_period_id)
    _ensure_asset(db, payload.asset_id)
    _ensure_unique(db, payload.contract_period_id, payload.asset_id)

    pa = PeriodAsset(**payload.model_dump())
    db.add(pa)
    db.commit()
    db.refresh(pa)
    return pa


def update_period_asset(db: Session, link_id: int, payload: PeriodAssetUpdate, current_user) -> PeriodAsset:
    _require_edit(current_user)
    pa = _get(db, link_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pa, field, value)
    db.commit()
    db.refresh(pa)
    return pa


def delete_period_asset(db: Session, link_id: int, current_user) -> None:
    _require_edit(current_user)
    pa = _get(db, link_id)
    db.delete(pa)
    db.commit()


# -- Private --


def _get(db: Session, link_id: int) -> PeriodAsset:
    pa = db.get(PeriodAsset, link_id)
    if pa is None:
        raise NotFoundError("Period-Asset link not found")
    return pa


def _ensure_period(db: Session, contract_period_id: int) -> None:
    if db.get(ContractPeriod, contract_period_id) is None:
        raise NotFoundError("Contract period not found")


def _ensure_asset(db: Session, asset_id: int) -> None:
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _ensure_unique(db: Session, contract_period_id: int, asset_id: int) -> None:
    existing = db.scalar(
        select(PeriodAsset).where(
            PeriodAsset.contract_period_id == contract_period_id,
            PeriodAsset.asset_id == asset_id,
        )
    )
    if existing:
        raise DuplicateError("This asset is already linked to the period")


def _require_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _enrich(db: Session, links: list[PeriodAsset]) -> list[dict]:
    if not links:
        return []
    asset_ids = {l.asset_id for l in links}
    period_ids = {l.contract_period_id for l in links}
    assets = {a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_(asset_ids)))}
    periods = {p.id: p for p in db.scalars(select(ContractPeriod).where(ContractPeriod.id.in_(period_ids)))}
    result = []
    for l in links:
        d = {c.key: getattr(l, c.key) for c in PeriodAsset.__table__.columns}
        d["created_at"] = l.created_at
        d["updated_at"] = l.updated_at
        a = assets.get(l.asset_id)
        p = periods.get(l.contract_period_id)
        d["asset_name"] = a.asset_name if a else None
        d["hostname"] = a.hostname if a else None
        d["period_label"] = p.period_label if p else None
        result.append(d)
    return result

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.partner import Partner
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_related_partner import AssetRelatedPartner
from app.modules.infra.models.period_partner import PeriodPartner
from app.modules.infra.services._helpers import get_period_asset_ids
from app.modules.infra.schemas.period_partner import (
    PeriodPartnerCreate,
    PeriodPartnerUpdate,
)


def list_by_period(db: Session, contract_period_id: int) -> list[dict]:
    links = list(
        db.scalars(
            select(PeriodPartner)
            .where(PeriodPartner.contract_period_id == contract_period_id)
            .order_by(PeriodPartner.id.asc())
        )
    )
    return _enrich(db, links)


def create_period_partner(
    db: Session, payload: PeriodPartnerCreate, current_user
) -> PeriodPartner:
    _require_edit(current_user)
    _ensure_period(db, payload.contract_period_id)
    _ensure_partner(db, payload.partner_id)
    _ensure_unique(db, payload.contract_period_id, payload.partner_id, payload.role)

    pp = PeriodPartner(**payload.model_dump())
    db.add(pp)
    db.commit()
    db.refresh(pp)
    return pp


def update_period_partner(
    db: Session, link_id: int, payload: PeriodPartnerUpdate, current_user
) -> PeriodPartner:
    _require_edit(current_user)
    pp = _get(db, link_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pp, field, value)
    db.commit()
    db.refresh(pp)
    return pp


def delete_period_partner(db: Session, link_id: int, current_user) -> None:
    _require_edit(current_user)
    pp = _get(db, link_id)
    db.delete(pp)
    db.commit()


# -- Private --


def _get(db: Session, link_id: int) -> PeriodPartner:
    pp = db.get(PeriodPartner, link_id)
    if pp is None:
        raise NotFoundError("Period-Partner link not found")
    return pp


def _ensure_period(db: Session, contract_period_id: int) -> None:
    if db.get(ContractPeriod, contract_period_id) is None:
        raise NotFoundError("Contract period not found")


def _ensure_partner(db: Session, partner_id: int) -> None:
    if db.get(Partner, partner_id) is None:
        raise NotFoundError("Partner not found")


def _ensure_unique(
    db: Session, contract_period_id: int, partner_id: int, role: str
) -> None:
    existing = db.scalar(
        select(PeriodPartner).where(
            PeriodPartner.contract_period_id == contract_period_id,
            PeriodPartner.partner_id == partner_id,
            PeriodPartner.role == role,
        )
    )
    if existing:
        raise DuplicateError("This partner-role is already linked to the period")


def _require_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _enrich(db: Session, links: list[PeriodPartner]) -> list[dict]:
    if not links:
        return []
    partner_ids = {l.partner_id for l in links}
    period_ids = {l.contract_period_id for l in links}
    partners = {
        p.id: p
        for p in db.scalars(select(Partner).where(Partner.id.in_(partner_ids)))
    }
    period_asset_map = _load_period_partner_assets(db, period_ids, partner_ids)
    result = []
    for l in links:
        d = {c.key: getattr(l, c.key) for c in PeriodPartner.__table__.columns}
        d["created_at"] = l.created_at
        d["updated_at"] = l.updated_at
        part = partners.get(l.partner_id)
        d["partner_name"] = part.name if part else None
        d["business_no"] = part.business_no if part else None
        d["assigned_assets"] = period_asset_map.get((l.contract_period_id, l.partner_id), [])
        result.append(d)
    return result


def _load_period_partner_assets(
    db: Session,
    period_ids: set[int],
    partner_ids: set[int],
) -> dict[tuple[int, int], list[dict]]:
    if not period_ids or not partner_ids:
        return {}

    period_asset_ids: dict[int, set[int]] = {
        period_id: get_period_asset_ids(db, period_id)
        for period_id in period_ids
    }
    all_asset_ids = {asset_id for asset_ids in period_asset_ids.values() for asset_id in asset_ids}
    if not all_asset_ids:
        return {}

    rows = list(
        db.execute(
            select(
                AssetRelatedPartner.partner_id,
                AssetRelatedPartner.relation_type,
                AssetRelatedPartner.is_primary,
                AssetRelatedPartner.note,
                Asset.id,
                Asset.asset_name,
                Asset.system_id,
                Asset.project_asset_number,
                Asset.hostname,
            )
            .join(Asset, Asset.id == AssetRelatedPartner.asset_id)
            .where(
                AssetRelatedPartner.partner_id.in_(partner_ids),
                AssetRelatedPartner.asset_id.in_(all_asset_ids),
            )
            .order_by(
                AssetRelatedPartner.partner_id.asc(),
                AssetRelatedPartner.is_primary.desc(),
                Asset.asset_name.asc(),
                Asset.id.asc(),
            )
        )
    )

    asset_rows_by_id: dict[int, list[dict]] = {}
    for partner_id, relation_type, is_primary, note, asset_id, asset_name, asset_system_id, project_asset_number, hostname in rows:
        asset_rows_by_id.setdefault(asset_id, []).append(
            {
                "partner_id": partner_id,
                "relation_type": relation_type,
                "is_primary": is_primary,
                "note": note,
                "id": asset_id,
                "asset_name": asset_name,
                "system_id": asset_system_id,
                "project_asset_number": project_asset_number,
                "hostname": hostname,
            }
        )

    result: dict[tuple[int, int], list[dict]] = {}
    for period_id, asset_ids in period_asset_ids.items():
        if not asset_ids:
            continue
        for asset_id in asset_ids:
            for item in asset_rows_by_id.get(asset_id, []):
                key = (period_id, item["partner_id"])
                result.setdefault(key, []).append(
                    {
                        "id": item["id"],
                        "asset_name": item["asset_name"],
                        "system_id": item["system_id"],
                        "project_asset_number": item["project_asset_number"],
                        "hostname": item["hostname"],
                        "relation_type": item["relation_type"],
                        "is_primary": item["is_primary"],
                        "note": item["note"],
                    }
                )

    return result

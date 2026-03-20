from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_relation import AssetRelation
from app.modules.infra.schemas.asset_relation import AssetRelationCreate, AssetRelationUpdate

VALID_RELATION_TYPES = {"HOSTS", "USES", "INSTALLED_ON", "PROTECTS", "CONNECTS_TO", "DEPENDS_ON"}


def list_by_asset(db: Session, asset_id: int) -> list[dict]:
    """자산의 모든 관계 조회 (src+dst 양방향)."""
    rels = list(
        db.scalars(
            select(AssetRelation)
            .where(
                or_(
                    AssetRelation.src_asset_id == asset_id,
                    AssetRelation.dst_asset_id == asset_id,
                )
            )
            .order_by(AssetRelation.id.asc())
        )
    )
    return _enrich(db, rels)


def list_by_customer(db: Session, customer_id: int) -> list[dict]:
    """고객사 소속 자산들의 모든 관계 조회."""
    asset_ids_q = select(Asset.id).where(Asset.customer_id == customer_id)
    rels = list(
        db.scalars(
            select(AssetRelation)
            .where(
                or_(
                    AssetRelation.src_asset_id.in_(asset_ids_q),
                    AssetRelation.dst_asset_id.in_(asset_ids_q),
                )
            )
            .order_by(AssetRelation.id.asc())
        )
    )
    return _enrich(db, rels)


def create_asset_relation(db: Session, payload: AssetRelationCreate, current_user) -> AssetRelation:
    _require_edit(current_user)

    if payload.src_asset_id == payload.dst_asset_id:
        raise BusinessRuleError("자기 자신과의 관계는 생성할 수 없습니다.")

    _ensure_asset(db, payload.src_asset_id)
    _ensure_asset(db, payload.dst_asset_id)

    rel = AssetRelation(**payload.model_dump())
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


def update_asset_relation(db: Session, rel_id: int, payload: AssetRelationUpdate, current_user) -> AssetRelation:
    _require_edit(current_user)
    rel = _get(db, rel_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rel, field, value)
    db.commit()
    db.refresh(rel)
    return rel


def delete_asset_relation(db: Session, rel_id: int, current_user) -> None:
    _require_edit(current_user)
    rel = _get(db, rel_id)
    db.delete(rel)
    db.commit()


# ── Private ──


def _get(db: Session, rel_id: int) -> AssetRelation:
    rel = db.get(AssetRelation, rel_id)
    if rel is None:
        raise NotFoundError("Asset relation not found")
    return rel


def _ensure_asset(db: Session, asset_id: int) -> None:
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _require_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _enrich(db: Session, rels: list[AssetRelation]) -> list[dict]:
    if not rels:
        return []
    asset_ids = set()
    for r in rels:
        asset_ids.add(r.src_asset_id)
        asset_ids.add(r.dst_asset_id)
    assets = {a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_(asset_ids)))}
    result = []
    for r in rels:
        d = {c.key: getattr(r, c.key) for c in AssetRelation.__table__.columns}
        d["created_at"] = r.created_at
        d["updated_at"] = r.updated_at
        src = assets.get(r.src_asset_id)
        dst = assets.get(r.dst_asset_id)
        d["src_asset_name"] = src.asset_name if src else None
        d["src_hostname"] = src.hostname if src else None
        d["dst_asset_name"] = dst.asset_name if dst else None
        d["dst_hostname"] = dst.hostname if dst else None
        result.append(d)
    return result

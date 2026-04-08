from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.modules.common.models.user import User
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_event import AssetEvent
from app.modules.infra.schemas.asset_event import AssetEventRead
from app.modules.infra.schemas.asset_event import AssetEventCreate


def list_asset_events(db: Session, asset_id: int) -> list[AssetEventRead]:
    _ensure_asset_exists(db, asset_id)
    related_asset = aliased(Asset)
    stmt = (
        select(AssetEvent, related_asset.asset_name, related_asset.system_id, User.name)
        .outerjoin(related_asset, related_asset.id == AssetEvent.related_asset_id)
        .outerjoin(User, User.id == AssetEvent.created_by_user_id)
        .where(AssetEvent.asset_id == asset_id)
        .order_by(AssetEvent.occurred_at.desc(), AssetEvent.id.desc())
    )
    rows = db.execute(stmt).all()
    return [
        _serialize_asset_event(event, related_name, related_code, user_name)
        for event, related_name, related_code, user_name in rows
    ]


def create_asset_event(
    db: Session, asset_id: int, payload: AssetEventCreate, current_user
) -> AssetEventRead:
    _require_inventory_edit(current_user)
    asset = _ensure_asset_exists(db, asset_id)
    if payload.related_asset_id is not None:
        _ensure_asset_exists(db, payload.related_asset_id)
    event = AssetEvent(
        asset_id=asset.id,
        related_asset_id=payload.related_asset_id,
        created_by_user_id=getattr(current_user, "id", None),
        event_type=payload.event_type,
        summary=payload.summary,
        detail=payload.detail,
        system_id_snapshot=asset.system_id,
        asset_name_snapshot=asset.asset_name,
        occurred_at=payload.occurred_at or datetime.now(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    related_asset = db.get(Asset, event.related_asset_id) if event.related_asset_id else None
    user_name = getattr(current_user, "name", None)
    return _serialize_asset_event(
        event,
        related_asset.asset_name if related_asset is not None else None,
        related_asset.system_id if related_asset is not None else None,
        user_name,
    )


def log_asset_event(
    db: Session,
    *,
    asset: Asset | None,
    event_type: str,
    summary: str,
    detail: str | None = None,
    created_by_user_id: int | None = None,
    related_asset_id: int | None = None,
    occurred_at: datetime | None = None,
) -> AssetEvent:
    event = AssetEvent(
        asset_id=asset.id if asset is not None else None,
        related_asset_id=related_asset_id,
        created_by_user_id=created_by_user_id,
        event_type=event_type,
        summary=summary,
        detail=detail,
        system_id_snapshot=asset.system_id if asset is not None else None,
        asset_name_snapshot=asset.asset_name if asset is not None else None,
        occurred_at=occurred_at or datetime.now(),
    )
    db.add(event)
    db.flush()
    return event


def _ensure_asset_exists(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _serialize_asset_event(
    event: AssetEvent,
    related_asset_name: str | None = None,
    related_asset_system_id: str | None = None,
    created_by_user_name: str | None = None,
) -> AssetEventRead:
    return AssetEventRead.model_validate(
        {
            "id": event.id,
            "asset_id": event.asset_id,
            "related_asset_id": event.related_asset_id,
            "created_by_user_id": event.created_by_user_id,
            "event_type": event.event_type,
            "summary": event.summary,
            "detail": event.detail,
            "related_asset_name": related_asset_name,
            "related_asset_code": related_asset_system_id,
            "created_by_user_name": created_by_user_name,
            "system_id_snapshot": event.system_id_snapshot,
            "asset_name_snapshot": event.asset_name_snapshot,
            "occurred_at": event.occurred_at,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }
    )

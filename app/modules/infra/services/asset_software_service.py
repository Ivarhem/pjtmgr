from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.modules.common.models.user import User
from app.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.asset_software import AssetSoftware
from app.modules.infra.schemas.asset_software import (
    AssetSoftwareCreate,
    AssetSoftwareUpdate,
)


def list_asset_software(db: Session, asset_id: int) -> list[AssetSoftware]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetSoftware)
            .where(AssetSoftware.asset_id == asset_id)
            .order_by(AssetSoftware.software_name.asc())
        )
    )


def get_asset_software(db: Session, software_id: int) -> AssetSoftware:
    sw = db.get(AssetSoftware, software_id)
    if sw is None:
        raise NotFoundError("Asset software not found")
    return sw


def create_asset_software(
    db: Session, payload: AssetSoftwareCreate, current_user: User
) -> AssetSoftware:
    _require_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)

    sw = AssetSoftware(**payload.model_dump())
    db.add(sw)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="asset_software",
        entity_id=None, summary=f"자산 SW 등록: {sw.software_name}", module="infra",
    )
    db.commit()
    db.refresh(sw)
    return sw


def update_asset_software(
    db: Session, software_id: int, payload: AssetSoftwareUpdate, current_user: User
) -> AssetSoftware:
    _require_edit(current_user)
    sw = get_asset_software(db, software_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(sw, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="asset_software",
        entity_id=sw.id, summary=f"자산 SW 수정: {sw.software_name}", module="infra",
    )
    db.commit()
    db.refresh(sw)
    return sw


def delete_asset_software(db: Session, software_id: int, current_user: User) -> None:
    _require_edit(current_user)
    sw = get_asset_software(db, software_id)
    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="asset_software",
        entity_id=sw.id, summary=f"자산 SW 삭제: {sw.software_name}", module="infra",
    )
    db.delete(sw)
    db.commit()


# ── Private helpers ──


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    from app.modules.infra.models.asset import Asset
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _require_edit(current_user: User) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_contact import AssetContact
from app.modules.infra.models.project import Project
from app.modules.infra.schemas.asset import AssetCreate, AssetUpdate
from app.modules.infra.schemas.asset_contact import (
    AssetContactCreate,
    AssetContactUpdate,
)
from app.modules.common.models.customer_contact import CustomerContact


# ── Asset ──


def list_assets(db: Session, project_id: int | None = None) -> list[Asset]:
    stmt = select(Asset)
    if project_id is not None:
        stmt = stmt.where(Asset.project_id == project_id)
    stmt = stmt.order_by(Asset.project_id.asc(), Asset.asset_name.asc())
    return list(db.scalars(stmt))


def get_asset(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def create_asset(db: Session, payload: AssetCreate, current_user) -> Asset:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)
    _ensure_asset_name_unique(db, payload.project_id, payload.asset_name)

    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(
    db: Session, asset_id: int, payload: AssetUpdate, current_user
) -> Asset:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    changes = payload.model_dump(exclude_unset=True)

    target_project_id = changes.get("project_id", asset.project_id)
    target_asset_name = changes.get("asset_name", asset.asset_name)

    if "project_id" in changes:
        _ensure_project_exists(db, target_project_id)

    if target_project_id != asset.project_id or target_asset_name != asset.asset_name:
        _ensure_asset_name_unique(db, target_project_id, target_asset_name, asset.id)

    for field, value in changes.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    db.delete(asset)
    db.commit()


# ── AssetContact ──


def list_asset_contacts(db: Session, asset_id: int) -> list[AssetContact]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetContact)
            .where(AssetContact.asset_id == asset_id)
            .order_by(AssetContact.id.asc())
        )
    )


def get_asset_contact(db: Session, asset_contact_id: int) -> AssetContact:
    ac = db.get(AssetContact, asset_contact_id)
    if ac is None:
        raise NotFoundError("Asset contact not found")
    return ac


def create_asset_contact(
    db: Session, payload: AssetContactCreate, current_user
) -> AssetContact:
    _require_inventory_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)
    _ensure_contact_exists(db, payload.contact_id)
    _ensure_asset_contact_unique(db, payload.asset_id, payload.contact_id, payload.role)

    ac = AssetContact(**payload.model_dump())
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def update_asset_contact(
    db: Session, asset_contact_id: int, payload: AssetContactUpdate, current_user
) -> AssetContact:
    _require_inventory_edit(current_user)
    ac = get_asset_contact(db, asset_contact_id)
    changes = payload.model_dump(exclude_unset=True)

    if "role" in changes:
        _ensure_asset_contact_unique(
            db, ac.asset_id, ac.contact_id, changes["role"], asset_contact_id
        )

    for field, value in changes.items():
        setattr(ac, field, value)

    db.commit()
    db.refresh(ac)
    return ac


def delete_asset_contact(db: Session, asset_contact_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    ac = get_asset_contact(db, asset_contact_id)
    db.delete(ac)
    db.commit()


# ── Private helpers ──


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _ensure_contact_exists(db: Session, contact_id: int) -> None:
    if db.get(CustomerContact, contact_id) is None:
        raise NotFoundError("Contact not found")


def _ensure_asset_name_unique(
    db: Session,
    project_id: int,
    asset_name: str,
    asset_id: int | None = None,
) -> None:
    stmt = select(Asset).where(
        Asset.project_id == project_id, Asset.asset_name == asset_name
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_id is not None and existing.id == asset_id:
        return
    raise DuplicateError("Asset name already exists in the project")


def _ensure_asset_contact_unique(
    db: Session,
    asset_id: int,
    contact_id: int,
    role: str | None,
    asset_contact_id: int | None = None,
) -> None:
    stmt = select(AssetContact).where(
        AssetContact.asset_id == asset_id,
        AssetContact.contact_id == contact_id,
        AssetContact.role == role,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_contact_id is not None and existing.id == asset_contact_id:
        return
    raise DuplicateError("This contact-role mapping already exists for the asset")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

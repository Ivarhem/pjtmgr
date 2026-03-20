from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_contact import AssetContact
from app.modules.infra.schemas.asset import AssetCreate, AssetUpdate
from app.modules.infra.services._helpers import ensure_customer_exists, get_project_asset_ids
from app.modules.infra.schemas.asset_contact import (
    AssetContactCreate,
    AssetContactUpdate,
)
from app.modules.common.models.customer_contact import CustomerContact


# ── Asset ──


def list_assets(
    db: Session,
    customer_id: int,
    project_id: int | None = None,
    asset_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> list[Asset]:
    stmt = select(Asset).where(Asset.customer_id == customer_id)
    if project_id is not None:
        asset_ids = get_project_asset_ids(db, project_id)
        if not asset_ids:
            return []
        stmt = stmt.where(Asset.id.in_(asset_ids))
    if asset_type is not None:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if status is not None:
        stmt = stmt.where(Asset.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            Asset.asset_name.ilike(like)
            | Asset.hostname.ilike(like)
            | Asset.service_ip.ilike(like)
            | Asset.equipment_id.ilike(like)
        )
    stmt = stmt.order_by(Asset.asset_name.asc())
    return list(db.scalars(stmt))


def enrich_assets_with_project(db: Session, assets: list[Asset]) -> list[dict]:
    """Attach project_code and project_name via ProjectAsset for inventory view."""
    from app.modules.infra.models.project import Project
    from app.modules.infra.models.project_asset import ProjectAsset

    if not assets:
        return []

    asset_ids = [a.id for a in assets]
    # Load ProjectAsset links for these assets
    pa_rows = list(
        db.execute(
            select(ProjectAsset.asset_id, ProjectAsset.project_id).where(
                ProjectAsset.asset_id.in_(asset_ids)
            )
        )
    )
    # Map asset_id -> first project_id (for display)
    asset_project_map: dict[int, int] = {}
    project_ids: set[int] = set()
    for row in pa_rows:
        if row.asset_id not in asset_project_map:
            asset_project_map[row.asset_id] = row.project_id
        project_ids.add(row.project_id)

    projects = {}
    if project_ids:
        projects = {
            p.id: p
            for p in db.scalars(select(Project).where(Project.id.in_(project_ids)))
        }

    result = []
    for a in assets:
        d = {c.key: getattr(a, c.key) for c in Asset.__table__.columns}
        d["created_at"] = a.created_at
        d["updated_at"] = a.updated_at
        proj_id = asset_project_map.get(a.id)
        proj = projects.get(proj_id) if proj_id else None
        d["project_code"] = proj.project_code if proj else None
        d["project_name"] = proj.project_name if proj else None
        result.append(d)
    return result


def get_asset(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def create_asset(db: Session, payload: AssetCreate, current_user) -> Asset:
    _require_inventory_edit(current_user)
    ensure_customer_exists(db, payload.customer_id)
    _ensure_asset_name_unique(db, payload.customer_id, payload.asset_name)

    asset = Asset(**payload.model_dump())
    db.add(asset)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="asset",
        entity_id=None, summary=f"자산 생성: {asset.asset_name}", module="infra",
    )
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(
    db: Session, asset_id: int, payload: AssetUpdate, current_user
) -> Asset:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    changes = payload.model_dump(exclude_unset=True)

    target_customer_id = changes.get("customer_id", asset.customer_id)
    target_asset_name = changes.get("asset_name", asset.asset_name)

    if "customer_id" in changes:
        ensure_customer_exists(db, target_customer_id)

    if target_customer_id != asset.customer_id or target_asset_name != asset.asset_name:
        _ensure_asset_name_unique(db, target_customer_id, target_asset_name, asset.id)

    for field, value in changes.items():
        setattr(asset, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="asset",
        entity_id=asset.id, summary=f"자산 수정: {asset.asset_name}", module="infra",
    )
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="asset",
        entity_id=asset.id, summary=f"자산 삭제: {asset.asset_name}", module="infra",
    )
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


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _ensure_contact_exists(db: Session, contact_id: int) -> None:
    if db.get(CustomerContact, contact_id) is None:
        raise NotFoundError("Contact not found")


def _ensure_asset_name_unique(
    db: Session,
    customer_id: int,
    asset_name: str,
    asset_id: int | None = None,
) -> None:
    stmt = select(Asset).where(
        Asset.customer_id == customer_id, Asset.asset_name == asset_name
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_id is not None and existing.id == asset_id:
        return
    raise DuplicateError("이 고객사에 동일한 자산명이 이미 존재합니다.")


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

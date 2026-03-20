from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.project import Project
from app.modules.infra.models.project_asset import ProjectAsset
from app.modules.infra.schemas.project_asset import ProjectAssetCreate, ProjectAssetUpdate


def list_by_project(db: Session, project_id: int) -> list[dict]:
    links = list(
        db.scalars(
            select(ProjectAsset)
            .where(ProjectAsset.project_id == project_id)
            .order_by(ProjectAsset.id.asc())
        )
    )
    return _enrich(db, links)


def list_by_asset(db: Session, asset_id: int) -> list[dict]:
    links = list(
        db.scalars(
            select(ProjectAsset)
            .where(ProjectAsset.asset_id == asset_id)
            .order_by(ProjectAsset.id.asc())
        )
    )
    return _enrich(db, links)


def create_project_asset(db: Session, payload: ProjectAssetCreate, current_user) -> ProjectAsset:
    _require_edit(current_user)
    _ensure_project(db, payload.project_id)
    _ensure_asset(db, payload.asset_id)
    _ensure_unique(db, payload.project_id, payload.asset_id)

    pa = ProjectAsset(**payload.model_dump())
    db.add(pa)
    db.commit()
    db.refresh(pa)
    return pa


def update_project_asset(db: Session, link_id: int, payload: ProjectAssetUpdate, current_user) -> ProjectAsset:
    _require_edit(current_user)
    pa = _get(db, link_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pa, field, value)
    db.commit()
    db.refresh(pa)
    return pa


def delete_project_asset(db: Session, link_id: int, current_user) -> None:
    _require_edit(current_user)
    pa = _get(db, link_id)
    db.delete(pa)
    db.commit()


def backfill_from_legacy(db: Session) -> int:
    """기존 Asset.project_id → project_assets 백필. 이미 존재하는 매핑은 건너뛰기."""
    assets = db.scalars(
        select(Asset).where(Asset.project_id.isnot(None))
    )
    created = 0
    for asset in assets:
        existing = db.scalar(
            select(ProjectAsset).where(
                ProjectAsset.project_id == asset.project_id,
                ProjectAsset.asset_id == asset.id,
            )
        )
        if existing:
            continue
        db.add(ProjectAsset(project_id=asset.project_id, asset_id=asset.id))
        created += 1
    if created:
        db.commit()
    return created


# ── Private ──


def _get(db: Session, link_id: int) -> ProjectAsset:
    pa = db.get(ProjectAsset, link_id)
    if pa is None:
        raise NotFoundError("Project-Asset link not found")
    return pa


def _ensure_project(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_asset(db: Session, asset_id: int) -> None:
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _ensure_unique(db: Session, project_id: int, asset_id: int) -> None:
    existing = db.scalar(
        select(ProjectAsset).where(
            ProjectAsset.project_id == project_id,
            ProjectAsset.asset_id == asset_id,
        )
    )
    if existing:
        raise DuplicateError("This asset is already linked to the project")


def _require_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _enrich(db: Session, links: list[ProjectAsset]) -> list[dict]:
    if not links:
        return []
    asset_ids = {l.asset_id for l in links}
    project_ids = {l.project_id for l in links}
    assets = {a.id: a for a in db.scalars(select(Asset).where(Asset.id.in_(asset_ids)))}
    projects = {p.id: p for p in db.scalars(select(Project).where(Project.id.in_(project_ids)))}
    result = []
    for l in links:
        d = {c.key: getattr(l, c.key) for c in ProjectAsset.__table__.columns}
        d["created_at"] = l.created_at
        d["updated_at"] = l.updated_at
        a = assets.get(l.asset_id)
        p = projects.get(l.project_id)
        d["asset_name"] = a.asset_name if a else None
        d["asset_type"] = a.asset_type if a else None
        d["hostname"] = a.hostname if a else None
        d["project_code"] = p.project_code if p else None
        d["project_name"] = p.project_name if p else None
        result.append(d)
    return result

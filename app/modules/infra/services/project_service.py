from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.project import Project
from app.modules.infra.schemas.project import ProjectCreate, ProjectUpdate


def list_projects(db: Session) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.project_code.asc())))


def get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


def create_project(db: Session, payload: ProjectCreate, current_user) -> Project:
    _require_inventory_edit(current_user)
    _ensure_project_code_unique(db, payload.project_code)

    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(
    db: Session, project_id: int, payload: ProjectUpdate, current_user
) -> Project:
    _require_inventory_edit(current_user)
    project = get_project(db, project_id)
    changes = payload.model_dump(exclude_unset=True)

    if "project_code" in changes and changes["project_code"] != project.project_code:
        _ensure_project_code_unique(db, changes["project_code"], project_id)

    for field, value in changes.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    project = get_project(db, project_id)

    has_assets = db.scalar(
        select(Asset.id).where(Asset.project_id == project_id).limit(1)
    )
    if has_assets is not None:
        raise BusinessRuleError("Project with assets cannot be deleted")

    db.delete(project)
    db.commit()


def _ensure_project_code_unique(
    db: Session, project_code: str, project_id: int | None = None
) -> None:
    stmt = select(Project).where(Project.project_code == project_code)
    existing = db.scalar(stmt)
    if existing is None:
        return
    if project_id is not None and existing.id == project_id:
        return
    raise DuplicateError("Project code already exists")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

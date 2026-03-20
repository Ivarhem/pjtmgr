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
from app.modules.common.services import audit
from app.modules.infra.models.project import Project
from app.modules.infra.models.project_asset import ProjectAsset
from app.modules.infra.schemas.project import ProjectCreate, ProjectUpdate
from app.modules.infra.services._helpers import ensure_customer_exists


def list_projects(
    db: Session, customer_id: int | None = None
) -> list[Project]:
    stmt = select(Project).order_by(Project.project_code.asc())
    if customer_id is not None:
        stmt = stmt.where(Project.customer_id == customer_id)
    return list(db.scalars(stmt))


def get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


def create_project(db: Session, payload: ProjectCreate, current_user) -> Project:
    _require_inventory_edit(current_user)
    ensure_customer_exists(db, payload.customer_id)
    _ensure_project_code_unique(db, payload.project_code)

    project = Project(**payload.model_dump())
    db.add(project)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="project",
        entity_id=None, summary=f"프로젝트 생성: {project.project_name}", module="infra",
    )
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

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="project",
        entity_id=project.id, summary=f"프로젝트 수정: {project.project_name}", module="infra",
    )
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    project = get_project(db, project_id)

    has_assets = db.scalar(
        select(ProjectAsset.id).where(ProjectAsset.project_id == project_id).limit(1)
    )
    if has_assets is not None:
        raise BusinessRuleError("Project with linked assets cannot be deleted")

    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="project",
        entity_id=project.id, summary=f"프로젝트 삭제: {project.project_name}", module="infra",
    )
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

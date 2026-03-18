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
from app.modules.infra.models.project import Project
from app.modules.infra.models.project_deliverable import ProjectDeliverable
from app.modules.infra.models.project_phase import ProjectPhase
from app.modules.infra.schemas.project_deliverable import (
    ProjectDeliverableCreate,
    ProjectDeliverableUpdate,
)
from app.modules.infra.schemas.project_phase import (
    ProjectPhaseCreate,
    ProjectPhaseUpdate,
)


# ── ProjectPhase ──


def list_phases(db: Session, project_id: int) -> list[ProjectPhase]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(ProjectPhase)
            .where(ProjectPhase.project_id == project_id)
            .order_by(ProjectPhase.id.asc())
        )
    )


def get_phase(db: Session, phase_id: int) -> ProjectPhase:
    phase = db.get(ProjectPhase, phase_id)
    if phase is None:
        raise NotFoundError("Project phase not found")
    return phase


def create_phase(
    db: Session, payload: ProjectPhaseCreate, current_user
) -> ProjectPhase:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)
    _ensure_phase_type_unique(db, payload.project_id, payload.phase_type)

    phase = ProjectPhase(**payload.model_dump())
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase


def update_phase(
    db: Session, phase_id: int, payload: ProjectPhaseUpdate, current_user
) -> ProjectPhase:
    _require_inventory_edit(current_user)
    phase = get_phase(db, phase_id)
    changes = payload.model_dump(exclude_unset=True)

    if "phase_type" in changes and changes["phase_type"] != phase.phase_type:
        _ensure_phase_type_unique(db, phase.project_id, changes["phase_type"], phase_id)

    for field, value in changes.items():
        setattr(phase, field, value)

    db.commit()
    db.refresh(phase)
    return phase


def delete_phase(db: Session, phase_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    phase = get_phase(db, phase_id)

    has_deliverables = db.scalar(
        select(ProjectDeliverable.id)
        .where(ProjectDeliverable.project_phase_id == phase_id)
        .limit(1)
    )
    if has_deliverables is not None:
        raise BusinessRuleError("Phase with deliverables cannot be deleted")

    db.delete(phase)
    db.commit()


# ── ProjectDeliverable ──


def list_deliverables(db: Session, phase_id: int) -> list[ProjectDeliverable]:
    _ensure_phase_exists(db, phase_id)
    return list(
        db.scalars(
            select(ProjectDeliverable)
            .where(ProjectDeliverable.project_phase_id == phase_id)
            .order_by(ProjectDeliverable.id.asc())
        )
    )


def get_deliverable(db: Session, deliverable_id: int) -> ProjectDeliverable:
    deliverable = db.get(ProjectDeliverable, deliverable_id)
    if deliverable is None:
        raise NotFoundError("Project deliverable not found")
    return deliverable


def create_deliverable(
    db: Session, payload: ProjectDeliverableCreate, current_user
) -> ProjectDeliverable:
    _require_inventory_edit(current_user)
    _ensure_phase_exists(db, payload.project_phase_id)

    deliverable = ProjectDeliverable(**payload.model_dump())
    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)
    return deliverable


def update_deliverable(
    db: Session,
    deliverable_id: int,
    payload: ProjectDeliverableUpdate,
    current_user,
) -> ProjectDeliverable:
    _require_inventory_edit(current_user)
    deliverable = get_deliverable(db, deliverable_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(deliverable, field, value)

    db.commit()
    db.refresh(deliverable)
    return deliverable


def delete_deliverable(db: Session, deliverable_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    deliverable = get_deliverable(db, deliverable_id)
    db.delete(deliverable)
    db.commit()


# ── Private helpers ──


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_phase_exists(db: Session, phase_id: int) -> None:
    if db.get(ProjectPhase, phase_id) is None:
        raise NotFoundError("Project phase not found")


def _ensure_phase_type_unique(
    db: Session, project_id: int, phase_type: str, phase_id: int | None = None
) -> None:
    stmt = select(ProjectPhase).where(
        ProjectPhase.project_id == project_id,
        ProjectPhase.phase_type == phase_type,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if phase_id is not None and existing.id == phase_id:
        return
    raise DuplicateError("Phase type already exists in this project")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

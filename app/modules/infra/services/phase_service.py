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
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.infra.models.period_deliverable import PeriodDeliverable
from app.modules.infra.models.period_phase import PeriodPhase
from app.modules.infra.schemas.period_deliverable import (
    PeriodDeliverableCreate,
    PeriodDeliverableUpdate,
)
from app.modules.infra.schemas.period_phase import (
    PeriodPhaseCreate,
    PeriodPhaseUpdate,
)


# -- PeriodPhase --


def list_phases(db: Session, contract_period_id: int) -> list[PeriodPhase]:
    _ensure_period_exists(db, contract_period_id)
    return list(
        db.scalars(
            select(PeriodPhase)
            .where(PeriodPhase.contract_period_id == contract_period_id)
            .order_by(PeriodPhase.id.asc())
        )
    )


def get_phase(db: Session, phase_id: int) -> PeriodPhase:
    phase = db.get(PeriodPhase, phase_id)
    if phase is None:
        raise NotFoundError("Period phase not found")
    return phase


def create_phase(
    db: Session, payload: PeriodPhaseCreate, current_user
) -> PeriodPhase:
    _require_inventory_edit(current_user)
    _ensure_period_exists(db, payload.contract_period_id)
    _ensure_phase_type_unique(db, payload.contract_period_id, payload.phase_type)

    phase = PeriodPhase(**payload.model_dump())
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase


def update_phase(
    db: Session, phase_id: int, payload: PeriodPhaseUpdate, current_user
) -> PeriodPhase:
    _require_inventory_edit(current_user)
    phase = get_phase(db, phase_id)
    changes = payload.model_dump(exclude_unset=True)

    if "phase_type" in changes and changes["phase_type"] != phase.phase_type:
        _ensure_phase_type_unique(db, phase.contract_period_id, changes["phase_type"], phase_id)

    for field, value in changes.items():
        setattr(phase, field, value)

    db.commit()
    db.refresh(phase)
    return phase


def delete_phase(db: Session, phase_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    phase = get_phase(db, phase_id)

    has_deliverables = db.scalar(
        select(PeriodDeliverable.id)
        .where(PeriodDeliverable.period_phase_id == phase_id)
        .limit(1)
    )
    if has_deliverables is not None:
        raise BusinessRuleError("Phase with deliverables cannot be deleted")

    db.delete(phase)
    db.commit()


# -- PeriodDeliverable --


def list_deliverables(db: Session, phase_id: int) -> list[PeriodDeliverable]:
    _ensure_phase_exists(db, phase_id)
    return list(
        db.scalars(
            select(PeriodDeliverable)
            .where(PeriodDeliverable.period_phase_id == phase_id)
            .order_by(PeriodDeliverable.id.asc())
        )
    )


def get_deliverable(db: Session, deliverable_id: int) -> PeriodDeliverable:
    deliverable = db.get(PeriodDeliverable, deliverable_id)
    if deliverable is None:
        raise NotFoundError("Period deliverable not found")
    return deliverable


def create_deliverable(
    db: Session, payload: PeriodDeliverableCreate, current_user
) -> PeriodDeliverable:
    _require_inventory_edit(current_user)
    _ensure_phase_exists(db, payload.period_phase_id)

    deliverable = PeriodDeliverable(**payload.model_dump())
    db.add(deliverable)
    db.commit()
    db.refresh(deliverable)
    return deliverable


def update_deliverable(
    db: Session,
    deliverable_id: int,
    payload: PeriodDeliverableUpdate,
    current_user,
) -> PeriodDeliverable:
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


# -- Private helpers --


def _ensure_period_exists(db: Session, contract_period_id: int) -> None:
    if db.get(ContractPeriod, contract_period_id) is None:
        raise NotFoundError("Contract period not found")


def _ensure_phase_exists(db: Session, phase_id: int) -> None:
    if db.get(PeriodPhase, phase_id) is None:
        raise NotFoundError("Period phase not found")


def _ensure_phase_type_unique(
    db: Session, contract_period_id: int, phase_type: str, phase_id: int | None = None
) -> None:
    stmt = select(PeriodPhase).where(
        PeriodPhase.contract_period_id == contract_period_id,
        PeriodPhase.phase_type == phase_type,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if phase_id is not None and existing.id == phase_id:
        return
    raise DuplicateError("Phase type already exists in this period")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

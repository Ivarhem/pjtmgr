from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.period_deliverable import (
    PeriodDeliverableCreate,
    PeriodDeliverableRead,
    PeriodDeliverableUpdate,
)
from app.modules.infra.services.phase_service import (
    create_deliverable,
    delete_deliverable,
    get_deliverable,
    list_deliverables,
    update_deliverable,
)


router = APIRouter(tags=["infra-period-deliverables"])


@router.get(
    "/api/v1/period-phases/{phase_id}/deliverables",
    response_model=list[PeriodDeliverableRead],
)
def list_deliverables_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PeriodDeliverableRead]:
    return list_deliverables(db, phase_id)


@router.post(
    "/api/v1/period-phases/{phase_id}/deliverables",
    response_model=PeriodDeliverableRead,
    status_code=status.HTTP_201_CREATED,
)
def create_deliverable_endpoint(
    phase_id: int,
    payload: PeriodDeliverableCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PeriodDeliverableRead:
    payload.period_phase_id = phase_id
    return create_deliverable(db, payload, current_user)


@router.get(
    "/api/v1/period-deliverables/{deliverable_id}",
    response_model=PeriodDeliverableRead,
)
def get_deliverable_endpoint(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PeriodDeliverableRead:
    return get_deliverable(db, deliverable_id)


@router.patch(
    "/api/v1/period-deliverables/{deliverable_id}",
    response_model=PeriodDeliverableRead,
)
def update_deliverable_endpoint(
    deliverable_id: int,
    payload: PeriodDeliverableUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PeriodDeliverableRead:
    return update_deliverable(db, deliverable_id, payload, current_user)


@router.delete(
    "/api/v1/period-deliverables/{deliverable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_deliverable_endpoint(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_deliverable(db, deliverable_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

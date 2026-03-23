from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.period_phase import (
    PeriodPhaseCreate,
    PeriodPhaseRead,
    PeriodPhaseUpdate,
)
from app.modules.infra.services.phase_service import (
    create_phase,
    delete_phase,
    get_phase,
    list_phases,
    update_phase,
)


router = APIRouter(tags=["infra-period-phases"])


@router.get(
    "/api/v1/contract-periods/{contract_period_id}/phases",
    response_model=list[PeriodPhaseRead],
)
def list_phases_endpoint(
    contract_period_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PeriodPhaseRead]:
    return list_phases(db, contract_period_id)


@router.post(
    "/api/v1/contract-periods/{contract_period_id}/phases",
    response_model=PeriodPhaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_phase_endpoint(
    contract_period_id: int,
    payload: PeriodPhaseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PeriodPhaseRead:
    payload.contract_period_id = contract_period_id
    return create_phase(db, payload, current_user)


@router.get(
    "/api/v1/period-phases/{phase_id}",
    response_model=PeriodPhaseRead,
)
def get_phase_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PeriodPhaseRead:
    return get_phase(db, phase_id)


@router.patch(
    "/api/v1/period-phases/{phase_id}",
    response_model=PeriodPhaseRead,
)
def update_phase_endpoint(
    phase_id: int,
    payload: PeriodPhaseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PeriodPhaseRead:
    return update_phase(db, phase_id, payload, current_user)


@router.delete(
    "/api/v1/period-phases/{phase_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_phase_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_phase(db, phase_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

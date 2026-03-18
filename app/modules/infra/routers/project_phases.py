from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.project_phase import (
    ProjectPhaseCreate,
    ProjectPhaseRead,
    ProjectPhaseUpdate,
)
from app.modules.infra.services.phase_service import (
    create_phase,
    delete_phase,
    get_phase,
    list_phases,
    update_phase,
)


router = APIRouter(tags=["infra-project-phases"])


@router.get(
    "/api/v1/projects/{project_id}/phases",
    response_model=list[ProjectPhaseRead],
)
def list_phases_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectPhaseRead]:
    return list_phases(db, project_id)


@router.post(
    "/api/v1/projects/{project_id}/phases",
    response_model=ProjectPhaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_phase_endpoint(
    project_id: int,
    payload: ProjectPhaseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectPhaseRead:
    payload.project_id = project_id
    return create_phase(db, payload, current_user)


@router.get(
    "/api/v1/project-phases/{phase_id}",
    response_model=ProjectPhaseRead,
)
def get_phase_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectPhaseRead:
    return get_phase(db, phase_id)


@router.patch(
    "/api/v1/project-phases/{phase_id}",
    response_model=ProjectPhaseRead,
)
def update_phase_endpoint(
    phase_id: int,
    payload: ProjectPhaseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectPhaseRead:
    return update_phase(db, phase_id, payload, current_user)


@router.delete(
    "/api/v1/project-phases/{phase_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_phase_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_phase(db, phase_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

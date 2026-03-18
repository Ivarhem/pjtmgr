from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.project_deliverable import (
    ProjectDeliverableCreate,
    ProjectDeliverableRead,
    ProjectDeliverableUpdate,
)
from app.modules.infra.services.phase_service import (
    create_deliverable,
    delete_deliverable,
    get_deliverable,
    list_deliverables,
    update_deliverable,
)


router = APIRouter(tags=["infra-project-deliverables"])


@router.get(
    "/api/v1/project-phases/{phase_id}/deliverables",
    response_model=list[ProjectDeliverableRead],
)
def list_deliverables_endpoint(
    phase_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectDeliverableRead]:
    return list_deliverables(db, phase_id)


@router.post(
    "/api/v1/project-phases/{phase_id}/deliverables",
    response_model=ProjectDeliverableRead,
    status_code=status.HTTP_201_CREATED,
)
def create_deliverable_endpoint(
    phase_id: int,
    payload: ProjectDeliverableCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectDeliverableRead:
    payload.project_phase_id = phase_id
    return create_deliverable(db, payload, current_user)


@router.get(
    "/api/v1/project-deliverables/{deliverable_id}",
    response_model=ProjectDeliverableRead,
)
def get_deliverable_endpoint(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectDeliverableRead:
    return get_deliverable(db, deliverable_id)


@router.patch(
    "/api/v1/project-deliverables/{deliverable_id}",
    response_model=ProjectDeliverableRead,
)
def update_deliverable_endpoint(
    deliverable_id: int,
    payload: ProjectDeliverableUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectDeliverableRead:
    return update_deliverable(db, deliverable_id, payload, current_user)


@router.delete(
    "/api/v1/project-deliverables/{deliverable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_deliverable_endpoint(
    deliverable_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_deliverable(db, deliverable_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

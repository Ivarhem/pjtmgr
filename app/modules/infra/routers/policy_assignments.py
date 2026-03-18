from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.policy_assignment import (
    PolicyAssignmentCreate,
    PolicyAssignmentRead,
    PolicyAssignmentUpdate,
)
from app.modules.infra.services.policy_service import (
    create_assignment,
    delete_assignment,
    get_assignment,
    list_assignments,
    update_assignment,
)


router = APIRouter(tags=["infra-policy-assignments"])


@router.get(
    "/api/v1/projects/{project_id}/policy-assignments",
    response_model=list[PolicyAssignmentRead],
)
def list_assignments_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PolicyAssignmentRead]:
    return list_assignments(db, project_id)


@router.post(
    "/api/v1/projects/{project_id}/policy-assignments",
    response_model=PolicyAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment_endpoint(
    project_id: int,
    payload: PolicyAssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyAssignmentRead:
    payload.project_id = project_id
    return create_assignment(db, payload, current_user)


@router.get(
    "/api/v1/policy-assignments/{assignment_id}",
    response_model=PolicyAssignmentRead,
)
def get_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyAssignmentRead:
    return get_assignment(db, assignment_id)


@router.patch(
    "/api/v1/policy-assignments/{assignment_id}",
    response_model=PolicyAssignmentRead,
)
def update_assignment_endpoint(
    assignment_id: int,
    payload: PolicyAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> PolicyAssignmentRead:
    return update_assignment(db, assignment_id, payload, current_user)


@router.delete(
    "/api/v1/policy-assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_assignment(db, assignment_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

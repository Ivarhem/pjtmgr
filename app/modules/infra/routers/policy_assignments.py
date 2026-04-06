from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
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


router = APIRouter(prefix="/api/v1/policy-assignments", tags=["infra-policy-assignments"])


@router.get("", response_model=list[PolicyAssignmentRead])
def list_assignments_endpoint(
    partner_id: int,
    period_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PolicyAssignmentRead]:
    return list_assignments(db, partner_id, period_id)


@router.post(
    "",
    response_model=PolicyAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment_endpoint(
    payload: PolicyAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PolicyAssignmentRead:
    return create_assignment(db, payload, current_user)


@router.get("/{assignment_id}", response_model=PolicyAssignmentRead)
def get_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PolicyAssignmentRead:
    return get_assignment(db, assignment_id)


@router.patch("/{assignment_id}", response_model=PolicyAssignmentRead)
def update_assignment_endpoint(
    assignment_id: int,
    payload: PolicyAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PolicyAssignmentRead:
    return update_assignment(db, assignment_id, payload, current_user)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_assignment(db, assignment_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

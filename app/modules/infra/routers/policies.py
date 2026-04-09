from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.policy_definition import (
    PolicyDefinitionCreate,
    PolicyDefinitionRead,
    PolicyDefinitionUpdate,
)
from app.modules.infra.services.policy_service import (
    create_policy,
    delete_policy,
    get_policy,
    list_policies,
    update_policy,
)


router = APIRouter(prefix="/api/v1/policies", tags=["infra-policies"])


@router.get("", response_model=list[PolicyDefinitionRead])
def list_policies_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PolicyDefinitionRead]:
    return list_policies(db)


@router.post(
    "", response_model=PolicyDefinitionRead, status_code=status.HTTP_201_CREATED
)
def create_policy_endpoint(
    payload: PolicyDefinitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PolicyDefinitionRead:
    return create_policy(db, payload, current_user)


@router.get("/{policy_id}", response_model=PolicyDefinitionRead)
def get_policy_endpoint(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PolicyDefinitionRead:
    return get_policy(db, policy_id)


@router.patch("/{policy_id}", response_model=PolicyDefinitionRead)
def update_policy_endpoint(
    policy_id: int,
    payload: PolicyDefinitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PolicyDefinitionRead:
    return update_policy(db, policy_id, payload, current_user)


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy_endpoint(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_policy(db, policy_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

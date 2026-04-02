from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.asset_role import (
    AssetRoleAssignmentCreate,
    AssetRoleAssignmentRead,
    AssetRoleAssignmentUpdate,
    AssetRoleCreate,
    AssetRoleRead,
    AssetRoleUpdate,
)
from app.modules.infra.schemas.asset_role_action import (
    AssetRoleActionResult,
    AssetRoleFailoverAction,
    AssetRoleReplacementAction,
    AssetRoleRepurposeAction,
)
from app.modules.infra.services.asset_role_service import (
    create_asset_role,
    create_asset_role_assignment,
    delete_asset_role,
    delete_asset_role_assignment,
    get_asset_role,
    list_asset_role_assignments,
    list_asset_roles,
    replace_asset_role_assignment,
    repurpose_asset_role_assignment,
    update_asset_role,
    update_asset_role_assignment,
)


router = APIRouter(prefix="/api/v1/asset-roles", tags=["infra-asset-roles"])


@router.get("", response_model=list[AssetRoleRead])
def list_asset_roles_endpoint(
    partner_id: int,
    contract_period_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetRoleRead]:
    return list_asset_roles(db, partner_id, contract_period_id, status)


@router.post("", response_model=AssetRoleRead, status_code=status.HTTP_201_CREATED)
def create_asset_role_endpoint(
    payload: AssetRoleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRoleRead:
    role = create_asset_role(db, payload, current_user)
    rows = [row for row in list_asset_roles(db, role.partner_id) if row["id"] == role.id]
    return rows[0]


@router.get("/{asset_role_id}", response_model=AssetRoleRead)
def get_asset_role_endpoint(
    asset_role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRoleRead:
    role = get_asset_role(db, asset_role_id)
    rows = [row for row in list_asset_roles(db, role.partner_id) if row["id"] == asset_role_id]
    return rows[0]


@router.patch("/{asset_role_id}", response_model=AssetRoleRead)
def update_asset_role_endpoint(
    asset_role_id: int,
    payload: AssetRoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRoleRead:
    role = update_asset_role(db, asset_role_id, payload, current_user)
    rows = [row for row in list_asset_roles(db, role.partner_id) if row["id"] == asset_role_id]
    return rows[0]


@router.delete("/{asset_role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset_role_endpoint(
    asset_role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_asset_role(db, asset_role_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{asset_role_id}/assignments", response_model=list[AssetRoleAssignmentRead])
def list_asset_role_assignments_endpoint(
    asset_role_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetRoleAssignmentRead]:
    return list_asset_role_assignments(db, asset_role_id)


@router.post("/{asset_role_id}/assignments", response_model=AssetRoleAssignmentRead, status_code=status.HTTP_201_CREATED)
def create_asset_role_assignment_endpoint(
    asset_role_id: int,
    payload: AssetRoleAssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRoleAssignmentRead:
    assignment = create_asset_role_assignment(db, asset_role_id, payload, current_user)
    rows = [row for row in list_asset_role_assignments(db, asset_role_id) if row["id"] == assignment.id]
    return rows[0]


@router.patch("/assignments/{assignment_id}", response_model=AssetRoleAssignmentRead)
def update_asset_role_assignment_endpoint(
    assignment_id: int,
    payload: AssetRoleAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRoleAssignmentRead:
    assignment = update_asset_role_assignment(db, assignment_id, payload, current_user)
    rows = [row for row in list_asset_role_assignments(db, assignment.asset_role_id) if row["id"] == assignment.id]
    return rows[0]


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset_role_assignment_endpoint(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_asset_role_assignment(db, assignment_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{asset_role_id}/actions/replacement", response_model=AssetRoleActionResult)
def replace_asset_role_endpoint(
    asset_role_id: int,
    payload: AssetRoleReplacementAction,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRoleActionResult:
    return replace_asset_role_assignment(
        db,
        asset_role_id,
        replacement_asset_id=payload.replacement_asset_id,
        occurred_at=payload.occurred_at,
        note=payload.note,
        current_user=current_user,
        event_type="replacement",
    )


@router.post("/{asset_role_id}/actions/failover", response_model=AssetRoleActionResult)
def failover_asset_role_endpoint(
    asset_role_id: int,
    payload: AssetRoleFailoverAction,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRoleActionResult:
    return replace_asset_role_assignment(
        db,
        asset_role_id,
        replacement_asset_id=payload.replacement_asset_id,
        occurred_at=payload.occurred_at,
        note=payload.note,
        current_user=current_user,
        event_type="failover",
    )


@router.post("/{asset_role_id}/actions/repurpose", response_model=AssetRoleActionResult)
def repurpose_asset_role_endpoint(
    asset_role_id: int,
    payload: AssetRoleRepurposeAction,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetRoleActionResult:
    return repurpose_asset_role_assignment(
        db,
        asset_role_id,
        new_role_name=payload.new_role_name,
        new_role_type=payload.new_role_type,
        new_contract_period_id=payload.new_contract_period_id,
        occurred_at=payload.occurred_at,
        note=payload.note,
        current_user=current_user,
    )

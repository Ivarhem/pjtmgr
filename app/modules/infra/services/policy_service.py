from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory, can_manage_policies
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.policy_assignment import PolicyAssignment
from app.modules.infra.models.policy_definition import PolicyDefinition
from app.modules.infra.models.project import Project
from app.modules.infra.schemas.policy_assignment import (
    PolicyAssignmentCreate,
    PolicyAssignmentUpdate,
)
from app.modules.infra.schemas.policy_definition import (
    PolicyDefinitionCreate,
    PolicyDefinitionUpdate,
)


# ── PolicyDefinition ──


def list_policies(db: Session) -> list[PolicyDefinition]:
    return list(
        db.scalars(
            select(PolicyDefinition).order_by(PolicyDefinition.policy_code.asc())
        )
    )


def get_policy(db: Session, policy_id: int) -> PolicyDefinition:
    policy = db.get(PolicyDefinition, policy_id)
    if policy is None:
        raise NotFoundError("Policy definition not found")
    return policy


def create_policy(
    db: Session, payload: PolicyDefinitionCreate, current_user
) -> PolicyDefinition:
    _require_policy_manage(current_user)
    _ensure_policy_code_unique(db, payload.policy_code)

    policy = PolicyDefinition(**payload.model_dump())
    db.add(policy)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="policy",
        entity_id=None, summary=f"정책 생성: {policy.policy_name}", module="infra",
    )
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(
    db: Session, policy_id: int, payload: PolicyDefinitionUpdate, current_user
) -> PolicyDefinition:
    _require_policy_manage(current_user)
    policy = get_policy(db, policy_id)
    changes = payload.model_dump(exclude_unset=True)

    if "policy_code" in changes and changes["policy_code"] != policy.policy_code:
        _ensure_policy_code_unique(db, changes["policy_code"], policy_id)

    for field, value in changes.items():
        setattr(policy, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="policy",
        entity_id=policy.id, summary=f"정책 수정: {policy.policy_name}", module="infra",
    )
    db.commit()
    db.refresh(policy)
    return policy


def delete_policy(db: Session, policy_id: int, current_user) -> None:
    _require_policy_manage(current_user)
    policy = get_policy(db, policy_id)

    has_assignments = db.scalar(
        select(PolicyAssignment.id)
        .where(PolicyAssignment.policy_definition_id == policy_id)
        .limit(1)
    )
    if has_assignments is not None:
        raise BusinessRuleError("Policy with assignments cannot be deleted")

    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="policy",
        entity_id=policy.id, summary=f"정책 삭제: {policy.policy_name}", module="infra",
    )
    db.delete(policy)
    db.commit()


# ── PolicyAssignment ──


def list_assignments(db: Session, project_id: int) -> list[PolicyAssignment]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(PolicyAssignment)
            .where(PolicyAssignment.project_id == project_id)
            .order_by(PolicyAssignment.id.asc())
        )
    )


def get_assignment(db: Session, assignment_id: int) -> PolicyAssignment:
    assignment = db.get(PolicyAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Policy assignment not found")
    return assignment


def create_assignment(
    db: Session, payload: PolicyAssignmentCreate, current_user
) -> PolicyAssignment:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)
    _ensure_policy_exists(db, payload.policy_definition_id)

    if payload.asset_id is not None:
        _ensure_asset_belongs_to_project(db, payload.asset_id, payload.project_id)

    _ensure_assignment_unique(
        db, payload.project_id, payload.asset_id, payload.policy_definition_id
    )

    assignment = PolicyAssignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def update_assignment(
    db: Session, assignment_id: int, payload: PolicyAssignmentUpdate, current_user
) -> PolicyAssignment:
    _require_inventory_edit(current_user)
    assignment = get_assignment(db, assignment_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(assignment, field, value)

    db.commit()
    db.refresh(assignment)
    return assignment


def delete_assignment(db: Session, assignment_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    assignment = get_assignment(db, assignment_id)
    db.delete(assignment)
    db.commit()


# ── Private helpers ──


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_policy_exists(db: Session, policy_id: int) -> None:
    if db.get(PolicyDefinition, policy_id) is None:
        raise NotFoundError("Policy definition not found")


def _ensure_policy_code_unique(
    db: Session, policy_code: str, policy_id: int | None = None
) -> None:
    stmt = select(PolicyDefinition).where(
        PolicyDefinition.policy_code == policy_code
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if policy_id is not None and existing.id == policy_id:
        return
    raise DuplicateError("Policy code already exists")


def _ensure_asset_belongs_to_project(
    db: Session, asset_id: int, project_id: int
) -> None:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    if asset.project_id != project_id:
        raise BusinessRuleError("Asset does not belong to this project")


def _ensure_assignment_unique(
    db: Session,
    project_id: int,
    asset_id: int | None,
    policy_definition_id: int,
    assignment_id: int | None = None,
) -> None:
    stmt = select(PolicyAssignment).where(
        PolicyAssignment.project_id == project_id,
        PolicyAssignment.asset_id == asset_id,
        PolicyAssignment.policy_definition_id == policy_definition_id,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if assignment_id is not None and existing.id == assignment_id:
        return
    raise DuplicateError("This policy assignment already exists")


def _require_policy_manage(current_user) -> None:
    if not can_manage_policies(current_user):
        raise PermissionDeniedError("Policy management permission required")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

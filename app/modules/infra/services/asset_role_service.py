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
from app.modules.common.models.partner import Partner
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_role import AssetRole
from app.modules.infra.models.asset_role_assignment import AssetRoleAssignment
from app.modules.infra.services.asset_event_service import log_asset_event


def list_asset_roles(
    db: Session,
    partner_id: int,
    contract_period_id: int | None = None,
    status: str | None = None,
) -> list[dict]:
    _ensure_partner_exists(db, partner_id)
    stmt = select(AssetRole).where(AssetRole.partner_id == partner_id)
    if contract_period_id is not None:
        stmt = stmt.where(AssetRole.contract_period_id == contract_period_id)
    if status is not None:
        stmt = stmt.where(AssetRole.status == status)
    stmt = stmt.order_by(AssetRole.role_name.asc(), AssetRole.id.asc())
    roles = list(db.scalars(stmt))
    return _enrich_roles_with_current_assignment(db, roles)


def get_asset_role(db: Session, asset_role_id: int) -> AssetRole:
    role = db.get(AssetRole, asset_role_id)
    if role is None:
        raise NotFoundError("Asset role not found")
    return role


def create_asset_role(db: Session, payload, current_user) -> AssetRole:
    _require_inventory_edit(current_user)
    _ensure_partner_exists(db, payload.partner_id)
    if payload.contract_period_id is not None:
        _ensure_period_belongs_to_partner(db, payload.contract_period_id, payload.partner_id)
    _ensure_role_name_unique(db, payload.partner_id, payload.role_name)
    role = AssetRole(**payload.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_asset_role(db: Session, asset_role_id: int, payload, current_user) -> AssetRole:
    _require_inventory_edit(current_user)
    role = get_asset_role(db, asset_role_id)
    changes = payload.model_dump(exclude_unset=True)
    target_name = changes.get("role_name", role.role_name)
    target_period_id = changes.get("contract_period_id", role.contract_period_id)
    _ensure_role_name_unique(db, role.partner_id, target_name, role.id)
    if target_period_id is not None:
        _ensure_period_belongs_to_partner(db, target_period_id, role.partner_id)
    for field, value in changes.items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return role


def delete_asset_role(db: Session, asset_role_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    role = get_asset_role(db, asset_role_id)
    db.delete(role)
    db.commit()


def list_asset_role_assignments(db: Session, asset_role_id: int) -> list[dict]:
    get_asset_role(db, asset_role_id)
    rows = list(
        db.execute(
            select(
                AssetRoleAssignment,
                Asset.asset_name,
                Asset.asset_code,
                Asset.status,
            )
            .join(Asset, Asset.id == AssetRoleAssignment.asset_id)
            .where(AssetRoleAssignment.asset_role_id == asset_role_id)
            .order_by(AssetRoleAssignment.is_current.desc(), AssetRoleAssignment.valid_from.desc(), AssetRoleAssignment.id.desc())
        )
    )
    result = []
    for assignment, asset_name, asset_code, asset_status in rows:
        result.append(
            {
                "id": assignment.id,
                "asset_role_id": assignment.asset_role_id,
                "asset_id": assignment.asset_id,
                "asset_name": asset_name,
                "asset_code": asset_code,
                "asset_status": asset_status,
                "assignment_type": assignment.assignment_type,
                "valid_from": assignment.valid_from,
                "valid_to": assignment.valid_to,
                "is_current": assignment.is_current,
                "note": assignment.note,
                "created_at": assignment.created_at,
                "updated_at": assignment.updated_at,
            }
        )
    return result


def get_asset_role_assignment(db: Session, assignment_id: int) -> AssetRoleAssignment:
    assignment = db.get(AssetRoleAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("Asset role assignment not found")
    return assignment


def create_asset_role_assignment(db: Session, asset_role_id: int, payload, current_user) -> AssetRoleAssignment:
    _require_inventory_edit(current_user)
    role = get_asset_role(db, asset_role_id)
    asset = _ensure_asset_exists(db, payload.asset_id)
    if asset.partner_id != role.partner_id:
        raise BusinessRuleError("역할과 자산의 고객사가 일치하지 않습니다.", status_code=422)
    _ensure_assignment_range(payload.valid_from, payload.valid_to)
    if payload.is_current:
        _clear_current_assignments(db, asset_role_id)
    assignment = AssetRoleAssignment(asset_role_id=asset_role_id, **payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def update_asset_role_assignment(db: Session, assignment_id: int, payload, current_user) -> AssetRoleAssignment:
    _require_inventory_edit(current_user)
    assignment = get_asset_role_assignment(db, assignment_id)
    changes = payload.model_dump(exclude_unset=True)
    target_valid_from = changes.get("valid_from", assignment.valid_from)
    target_valid_to = changes.get("valid_to", assignment.valid_to)
    _ensure_assignment_range(target_valid_from, target_valid_to)
    if changes.get("is_current") is True:
        _clear_current_assignments(db, assignment.asset_role_id, exclude_assignment_id=assignment.id)
    for field, value in changes.items():
        setattr(assignment, field, value)
    if assignment.valid_to is not None and assignment.is_current:
        assignment.is_current = False
    db.commit()
    db.refresh(assignment)
    return assignment


def delete_asset_role_assignment(db: Session, assignment_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    assignment = get_asset_role_assignment(db, assignment_id)
    db.delete(assignment)
    db.commit()


def replace_asset_role_assignment(
    db: Session,
    asset_role_id: int,
    *,
    replacement_asset_id: int,
    occurred_at,
    note: str | None,
    current_user,
    event_type: str = "replacement",
) -> dict:
    _require_inventory_edit(current_user)
    role = get_asset_role(db, asset_role_id)
    current_assignment = _get_current_assignment(db, asset_role_id)
    if current_assignment is None:
        raise BusinessRuleError("현재 담당 자산이 없는 역할입니다.", status_code=422)

    current_asset = _ensure_asset_exists(db, current_assignment.asset_id)
    replacement_asset = _ensure_asset_exists(db, replacement_asset_id)
    if replacement_asset.partner_id != role.partner_id:
        raise BusinessRuleError("대상 자산의 고객사가 역할과 일치하지 않습니다.", status_code=422)
    if replacement_asset.id == current_asset.id:
        raise BusinessRuleError("현재 담당 자산과 동일한 자산으로는 처리할 수 없습니다.", status_code=422)

    effective_at = occurred_at or current_asset.updated_at
    effective_date = effective_at.date() if hasattr(effective_at, "date") else None

    current_assignment.valid_to = effective_date
    current_assignment.is_current = False

    new_assignment = AssetRoleAssignment(
        asset_role_id=asset_role_id,
        asset_id=replacement_asset.id,
        assignment_type="primary" if event_type == "replacement" else "temporary",
        valid_from=effective_date,
        valid_to=None,
        is_current=True,
        note=note,
    )
    db.add(new_assignment)
    db.flush()

    event_label = "교체" if event_type == "replacement" else "장애 대체"
    detail = "\n".join(
        [
            f"역할: {role.role_name}",
            f"이전 자산: {current_asset.asset_name} ({current_asset.asset_code or '코드없음'})",
            f"신규 자산: {replacement_asset.asset_name} ({replacement_asset.asset_code or '코드없음'})",
            f"메모: {note}" if note else "",
        ]
    ).strip()
    log_asset_event(
        db,
        asset=current_asset,
        event_type=event_type,
        summary=f"{role.role_name} {event_label}",
        detail=detail,
        created_by_user_id=getattr(current_user, "id", None),
        related_asset_id=replacement_asset.id,
        occurred_at=occurred_at,
    )
    log_asset_event(
        db,
        asset=replacement_asset,
        event_type=event_type,
        summary=f"{role.role_name} {event_label} 배정",
        detail=detail,
        created_by_user_id=getattr(current_user, "id", None),
        related_asset_id=current_asset.id,
        occurred_at=occurred_at,
    )
    db.commit()
    return {
        "source_role_id": role.id,
        "source_assignment_id": current_assignment.id,
        "target_role_id": role.id,
        "target_assignment_id": new_assignment.id,
        "message": f"{event_label} 처리되었습니다.",
    }


def repurpose_asset_role_assignment(
    db: Session,
    asset_role_id: int,
    *,
    new_role_name: str,
    new_contract_period_id: int | None,
    occurred_at,
    note: str | None,
    current_user,
) -> dict:
    _require_inventory_edit(current_user)
    source_role = get_asset_role(db, asset_role_id)
    current_assignment = _get_current_assignment(db, asset_role_id)
    if current_assignment is None:
        raise BusinessRuleError("현재 담당 자산이 없는 역할입니다.", status_code=422)

    asset = _ensure_asset_exists(db, current_assignment.asset_id)
    target_period_id = new_contract_period_id if new_contract_period_id is not None else source_role.contract_period_id
    if target_period_id is not None:
        _ensure_period_belongs_to_partner(db, target_period_id, source_role.partner_id)
    _ensure_role_name_unique(db, source_role.partner_id, new_role_name)

    effective_at = occurred_at or asset.updated_at
    effective_date = effective_at.date() if hasattr(effective_at, "date") else None

    current_assignment.valid_to = effective_date
    current_assignment.is_current = False

    target_role = AssetRole(
        partner_id=source_role.partner_id,
        contract_period_id=target_period_id,
        role_name=new_role_name,
        status="active",
        note=note,
    )
    db.add(target_role)
    db.flush()

    target_assignment = AssetRoleAssignment(
        asset_role_id=target_role.id,
        asset_id=asset.id,
        assignment_type="primary",
        valid_from=effective_date,
        valid_to=None,
        is_current=True,
        note=note,
    )
    db.add(target_assignment)
    db.flush()

    detail = "\n".join(
        [
            f"기존 역할: {source_role.role_name}",
            f"신규 역할: {target_role.role_name}",
            f"자산: {asset.asset_name} ({asset.asset_code or '코드없음'})",
            f"메모: {note}" if note else "",
        ]
    ).strip()
    log_asset_event(
        db,
        asset=asset,
        event_type="repurpose",
        summary=f"{source_role.role_name} -> {target_role.role_name} 용도 전환",
        detail=detail,
        created_by_user_id=getattr(current_user, "id", None),
        occurred_at=occurred_at,
    )
    db.commit()
    return {
        "source_role_id": source_role.id,
        "source_assignment_id": current_assignment.id,
        "target_role_id": target_role.id,
        "target_assignment_id": target_assignment.id,
        "message": "용도 전환 처리되었습니다.",
    }


def _enrich_roles_with_current_assignment(db: Session, roles: list[AssetRole]) -> list[dict]:
    if not roles:
        return []
    role_ids = [role.id for role in roles]
    current_assignments = list(
        db.execute(
            select(AssetRoleAssignment, Asset.asset_name, Asset.asset_code, Asset.status)
            .join(Asset, Asset.id == AssetRoleAssignment.asset_id)
            .where(
                AssetRoleAssignment.asset_role_id.in_(role_ids),
                AssetRoleAssignment.is_current.is_(True),
            )
            .order_by(AssetRoleAssignment.id.desc())
        )
    )
    current_map = {}
    for assignment, asset_name, asset_code, asset_status in current_assignments:
        current_map.setdefault(
            assignment.asset_role_id,
            {
                "current_assignment_id": assignment.id,
                "current_asset_id": assignment.asset_id,
                "current_asset_name": asset_name,
                "current_asset_code": asset_code,
                "current_asset_status": asset_status,
            },
        )

    result = []
    for role in roles:
        item = {column.key: getattr(role, column.key) for column in AssetRole.__table__.columns}
        item["created_at"] = role.created_at
        item["updated_at"] = role.updated_at
        item.update(
            current_map.get(
                role.id,
                {
                    "current_assignment_id": None,
                    "current_asset_id": None,
                    "current_asset_name": None,
                    "current_asset_code": None,
                    "current_asset_status": None,
                },
            )
        )
        result.append(item)
    return result


def _clear_current_assignments(
    db: Session,
    asset_role_id: int,
    exclude_assignment_id: int | None = None,
) -> None:
    rows = list(
        db.scalars(
            select(AssetRoleAssignment).where(
                AssetRoleAssignment.asset_role_id == asset_role_id,
                AssetRoleAssignment.is_current.is_(True),
            )
        )
    )
    for row in rows:
        if exclude_assignment_id is not None and row.id == exclude_assignment_id:
            continue
        row.is_current = False


def _get_current_assignment(db: Session, asset_role_id: int) -> AssetRoleAssignment | None:
    return db.scalar(
        select(AssetRoleAssignment).where(
            AssetRoleAssignment.asset_role_id == asset_role_id,
            AssetRoleAssignment.is_current.is_(True),
        ).order_by(AssetRoleAssignment.id.desc())
    )


def _ensure_partner_exists(db: Session, partner_id: int) -> Partner:
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise NotFoundError("Partner not found")
    return partner


def _ensure_asset_exists(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def _ensure_period_belongs_to_partner(db: Session, contract_period_id: int, partner_id: int) -> None:
    period = db.get(ContractPeriod, contract_period_id)
    if period is None:
        raise NotFoundError("Contract period not found")
    period_partner_id = period.partner_id
    contract_partner_id = period.contract.end_partner_id if period.contract else None
    if period_partner_id != partner_id and contract_partner_id != partner_id:
        raise BusinessRuleError("선택한 귀속사업이 현재 고객사와 일치하지 않습니다.", status_code=422)


def _ensure_role_name_unique(
    db: Session,
    partner_id: int,
    role_name: str,
    asset_role_id: int | None = None,
) -> None:
    stmt = select(AssetRole).where(
        AssetRole.partner_id == partner_id,
        AssetRole.role_name == role_name,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_role_id is not None and existing.id == asset_role_id:
        return
    raise DuplicateError("이 고객사에 동일한 역할명이 이미 존재합니다.")


def _ensure_assignment_range(valid_from, valid_to) -> None:
    if valid_from is not None and valid_to is not None and valid_from > valid_to:
        raise BusinessRuleError("할당 시작일은 종료일보다 늦을 수 없습니다.", status_code=422)


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

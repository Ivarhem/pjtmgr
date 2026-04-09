from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.auth.authorization import can_manage_catalog_taxonomy
from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.infra.models.classification_node import ClassificationNode
from app.modules.infra.models.classification_scheme import ClassificationScheme
from app.modules.infra.schemas.classification_node import ClassificationNodeCreate, ClassificationNodeUpdate
from app.modules.infra.schemas.classification_scheme import (
    ClassificationSchemeCopyRequest,
    ClassificationSchemeCreate,
    ClassificationSchemeInitRequest,
    ClassificationSchemeUpdate,
)


def list_classification_schemes(
    db: Session,
    *,
    scope_type: str | None = None,
    project_id: int | None = None,
    partner_id: int | None = None,
) -> list[dict]:
    stmt = (
        select(ClassificationScheme)
        .options(
            joinedload(ClassificationScheme.project).joinedload(ContractPeriod.contract),
            joinedload(ClassificationScheme.source_scheme),
        )
        .order_by(ClassificationScheme.scope_type.asc(), ClassificationScheme.name.asc(), ClassificationScheme.id.asc())
    )
    if scope_type:
        stmt = stmt.where(ClassificationScheme.scope_type == scope_type)
    if project_id is not None:
        stmt = stmt.where(ClassificationScheme.project_id == project_id)
    if partner_id is not None:
        stmt = (
            stmt.join(ContractPeriod, ContractPeriod.id == ClassificationScheme.project_id, isouter=True)
            .join(Contract, Contract.id == ContractPeriod.contract_id, isouter=True)
            .where(
                or_(
                    ContractPeriod.partner_id == partner_id,
                    Contract.end_partner_id == partner_id,
                )
            )
        )
    schemes = list(db.scalars(stmt).unique())
    if not schemes:
        return []

    count_rows = db.execute(
        select(ClassificationNode.scheme_id, func.count(ClassificationNode.id))
        .where(ClassificationNode.scheme_id.in_([scheme.id for scheme in schemes]))
        .group_by(ClassificationNode.scheme_id)
    ).all()
    node_count_map = {scheme_id: int(count) for scheme_id, count in count_rows}
    return [_scheme_to_dict(scheme, node_count_map.get(scheme.id, 0)) for scheme in schemes]


def create_classification_scheme(
    db: Session,
    payload: ClassificationSchemeCreate,
    current_user,
) -> ClassificationScheme:
    _require_inventory_edit(current_user)
    _ensure_scope(payload.scope_type, payload.project_id)
    _ensure_scheme_name_unique(db, payload.scope_type, payload.project_id, payload.name)
    if payload.project_id is not None:
        _ensure_project_exists(db, payload.project_id)
    scheme = ClassificationScheme(**payload.model_dump())
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return scheme


def update_classification_scheme(
    db: Session,
    scheme_id: int,
    payload: ClassificationSchemeUpdate,
    current_user,
) -> ClassificationScheme:
    _require_inventory_edit(current_user)
    scheme = get_classification_scheme(db, scheme_id)
    changes = payload.model_dump(exclude_unset=True)
    target_name = changes.get("name", scheme.name)
    if target_name != scheme.name:
        _ensure_scheme_name_unique(db, scheme.scope_type, scheme.project_id, target_name, scheme.id)
    for field, value in changes.items():
        setattr(scheme, field, value)
    db.commit()
    db.refresh(scheme)
    return scheme


def delete_classification_scheme(db: Session, scheme_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    scheme = get_classification_scheme(db, scheme_id)
    if scheme.scope_type == "global":
        raise BusinessRuleError("글로벌 기본 분류체계는 직접 삭제할 수 없습니다.", status_code=409)
    db.delete(scheme)
    db.commit()


def copy_classification_scheme(
    db: Session,
    scheme_id: int,
    payload: ClassificationSchemeCopyRequest,
    current_user,
) -> ClassificationScheme:
    _require_inventory_edit(current_user)
    source = get_classification_scheme(db, scheme_id)
    target_scope = "project" if payload.target_project_id else source.scope_type
    _ensure_scope(target_scope, payload.target_project_id)
    if payload.target_project_id is not None:
        _ensure_project_exists(db, payload.target_project_id)
    target_name = payload.name or (
        f"{source.name} 복사본" if source.project_id == payload.target_project_id else source.name
    )
    _ensure_scheme_name_unique(db, target_scope, payload.target_project_id, target_name)

    copied = ClassificationScheme(
        scope_type=target_scope,
        project_id=payload.target_project_id,
        name=target_name,
        description=payload.description if payload.description is not None else source.description,
        level_1_alias=source.level_1_alias,
        level_2_alias=source.level_2_alias,
        level_3_alias=source.level_3_alias,
        level_4_alias=source.level_4_alias,
        level_5_alias=source.level_5_alias,
        source_scheme_id=source.id,
        is_active=True,
    )
    db.add(copied)
    db.flush()

    source_nodes = list(
        db.scalars(
            select(ClassificationNode)
            .where(ClassificationNode.scheme_id == source.id)
            .order_by(ClassificationNode.level.asc(), ClassificationNode.sort_order.asc(), ClassificationNode.id.asc())
        )
    )
    id_map: dict[int, int] = {}
    for node in source_nodes:
        normalized_node_meta = _normalize_asset_type_meta(
            node.asset_type_key,
            node.asset_type_code,
            node.asset_type_label,
            node.asset_kind,
            node.is_catalog_assignable,
        )
        cloned = ClassificationNode(
            scheme_id=copied.id,
            parent_id=id_map.get(node.parent_id),
            node_code=node.node_code,
            node_name=node.node_name,
            level=node.level,
            sort_order=node.sort_order,
            is_active=node.is_active,
            asset_type_key=normalized_node_meta["asset_type_key"],
            asset_type_code=normalized_node_meta["asset_type_code"],
            asset_type_label=normalized_node_meta["asset_type_label"],
            asset_kind=normalized_node_meta["asset_kind"],
            is_catalog_assignable=normalized_node_meta["is_catalog_assignable"],
            note=node.note,
        )
        db.add(cloned)
        db.flush()
        id_map[node.id] = cloned.id

    db.commit()
    db.refresh(copied)
    return copied


def list_classification_scheme_sources(
    db: Session,
    *,
    partner_id: int,
) -> dict:
    global_schemes = list_classification_schemes(db, scope_type="global")
    project_schemes = list_classification_schemes(db, scope_type="project", partner_id=partner_id)
    return {
        "global_schemes": global_schemes,
        "partner_project_schemes": project_schemes,
    }


def initialize_project_classification_scheme(
    db: Session,
    *,
    project_id: int,
    payload: ClassificationSchemeInitRequest,
    current_user,
) -> ClassificationScheme:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, project_id)
    existing = db.scalar(
        select(ClassificationScheme).where(
            ClassificationScheme.scope_type == "project",
            ClassificationScheme.project_id == project_id,
        )
    )
    if existing is not None:
        raise DuplicateError("이미 프로젝트 분류체계가 초기화되어 있습니다.")

    mode = payload.mode.strip().lower()
    if mode not in {"global", "partner_project"}:
        raise BusinessRuleError("mode는 global 또는 partner_project 여야 합니다.", status_code=422)
    if payload.source_scheme_id is None:
        raise BusinessRuleError("선택한 초기화 방식에는 source_scheme_id가 필요합니다.", status_code=422)

    source = get_classification_scheme(db, payload.source_scheme_id)
    if mode == "global" and source.scope_type != "global":
        raise BusinessRuleError("글로벌 기본 분류체계만 선택할 수 있습니다.", status_code=422)
    if mode == "partner_project":
        project = _ensure_project_exists(db, project_id)
        project_partner_id = project.partner_id or (project.contract.end_partner_id if project.contract else None)
        source_project = _ensure_project_exists(db, source.project_id) if source.project_id else None
        source_partner_id = source_project.partner_id if source_project else None
        if source.scope_type != "project" or source_partner_id != project_partner_id:
            raise BusinessRuleError("같은 고객사의 기존 프로젝트 분류체계만 선택할 수 있습니다.", status_code=422)

    copy_payload = ClassificationSchemeCopyRequest(
        target_project_id=project_id,
        name=payload.name,
        description=payload.description,
    )
    return copy_classification_scheme(db, source.id, copy_payload, current_user)


def list_classification_nodes(db: Session, scheme_id: int) -> list[dict]:
    scheme = get_classification_scheme(db, scheme_id)
    rows = list(
        db.scalars(
            select(ClassificationNode)
            .where(ClassificationNode.scheme_id == scheme.id)
            .order_by(ClassificationNode.level.asc(), ClassificationNode.sort_order.asc(), ClassificationNode.id.asc())
        )
    )
    node_map = {row.id: row for row in rows}
    return [_node_to_dict(row, node_map) for row in rows]


def create_classification_node(
    db: Session,
    scheme_id: int,
    payload: ClassificationNodeCreate,
    current_user,
) -> ClassificationNode:
    _require_inventory_edit(current_user)
    scheme = get_classification_scheme(db, scheme_id)
    parent = _get_parent_node(db, scheme.id, payload.parent_id)
    level = payload.level or ((parent.level + 1) if parent else 1)
    _ensure_node_code_unique(db, scheme.id, payload.node_code)
    normalized_node_meta = _normalize_asset_type_meta(
        payload.asset_type_key,
        payload.asset_type_code,
        payload.asset_type_label,
        payload.asset_kind,
        payload.is_catalog_assignable,
    )
    node = ClassificationNode(
        scheme_id=scheme.id,
        parent_id=parent.id if parent else None,
        node_code=payload.node_code,
        node_name=payload.node_name,
        level=level,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        asset_type_key=normalized_node_meta["asset_type_key"],
        asset_type_code=normalized_node_meta["asset_type_code"],
        asset_type_label=normalized_node_meta["asset_type_label"],
        asset_kind=normalized_node_meta["asset_kind"],
        is_catalog_assignable=normalized_node_meta["is_catalog_assignable"],
        note=payload.note,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def update_classification_node(
    db: Session,
    node_id: int,
    payload: ClassificationNodeUpdate,
    current_user,
) -> ClassificationNode:
    _require_inventory_edit(current_user)
    node = get_classification_node(db, node_id)
    changes = payload.model_dump(exclude_unset=True)
    if "node_code" in changes and changes["node_code"] != node.node_code:
        _ensure_node_code_unique(db, node.scheme_id, changes["node_code"], node.id)
    if "parent_id" in changes:
        parent = _get_parent_node(db, node.scheme_id, changes["parent_id"], node.id)
        changes["parent_id"] = parent.id if parent else None
        if "level" not in changes:
            changes["level"] = (parent.level + 1) if parent else 1
    if (
        "asset_type_key" in changes
        or "asset_type_code" in changes
        or "asset_type_label" in changes
        or "asset_kind" in changes
        or "is_catalog_assignable" in changes
    ):
        normalized_node_meta = _normalize_asset_type_meta(
            changes.get("asset_type_key", node.asset_type_key),
            changes.get("asset_type_code", node.asset_type_code),
            changes.get("asset_type_label", node.asset_type_label),
            changes.get("asset_kind", node.asset_kind),
            changes.get("is_catalog_assignable", node.is_catalog_assignable),
        )
        changes.update(normalized_node_meta)
    for field, value in changes.items():
        setattr(node, field, value)
    db.commit()
    db.refresh(node)
    return node


def delete_classification_node(db: Session, node_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    node = get_classification_node(db, node_id)
    db.delete(node)
    db.commit()


def get_classification_scheme(db: Session, scheme_id: int) -> ClassificationScheme:
    scheme = db.get(ClassificationScheme, scheme_id)
    if scheme is None:
        raise NotFoundError("Classification scheme not found")
    return scheme


def get_classification_node(db: Session, node_id: int) -> ClassificationNode:
    node = db.get(ClassificationNode, node_id)
    if node is None:
        raise NotFoundError("Classification node not found")
    return node


def _scheme_to_dict(scheme: ClassificationScheme, node_count: int) -> dict:
    project_label = None
    if scheme.project is not None:
        contract_name = scheme.project.contract.contract_name if scheme.project.contract else None
        project_label = " · ".join(part for part in [scheme.project.period_label, contract_name] if part)
    return {
        "id": scheme.id,
        "scope_type": scheme.scope_type,
        "project_id": scheme.project_id,
        "project_label": project_label,
        "name": scheme.name,
        "description": scheme.description,
        "level_1_alias": scheme.level_1_alias,
        "level_2_alias": scheme.level_2_alias,
        "level_3_alias": scheme.level_3_alias,
        "level_4_alias": scheme.level_4_alias,
        "level_5_alias": scheme.level_5_alias,
        "source_scheme_id": scheme.source_scheme_id,
        "source_scheme_name": scheme.source_scheme.name if scheme.source_scheme else None,
        "is_active": scheme.is_active,
        "node_count": int(node_count or 0),
        "created_at": scheme.created_at,
        "updated_at": scheme.updated_at,
    }


def _node_to_dict(node: ClassificationNode, node_map: dict[int, ClassificationNode]) -> dict:
    path_parts = [node.node_name]
    parent_id = node.parent_id
    while parent_id:
        parent = node_map.get(parent_id)
        if parent is None:
            break
        path_parts.append(parent.node_name)
        parent_id = parent.parent_id
    path_parts.reverse()
    return {
        "id": node.id,
        "scheme_id": node.scheme_id,
        "parent_id": node.parent_id,
        "node_code": node.node_code,
        "node_name": node.node_name,
        "level": node.level,
        "sort_order": node.sort_order,
        "is_active": node.is_active,
        "asset_type_key": node.asset_type_key,
        "asset_type_code": node.asset_type_code,
        "asset_type_label": node.asset_type_label,
        "asset_kind": node.asset_kind,
        "is_catalog_assignable": node.is_catalog_assignable,
        "note": node.note,
        "path_label": " > ".join(path_parts),
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


def _require_inventory_edit(current_user) -> None:
    if not can_manage_catalog_taxonomy(current_user):
        raise PermissionDeniedError("카탈로그 기준체계 수정 권한이 없습니다.")


def _ensure_scope(scope_type: str, project_id: int | None) -> None:
    if scope_type not in {"global", "project"}:
        raise BusinessRuleError("scope_type은 global 또는 project 여야 합니다.", status_code=422)
    if scope_type == "global" and project_id is not None:
        raise BusinessRuleError("global 분류체계는 project_id를 가질 수 없습니다.", status_code=422)
    if scope_type == "project" and project_id is None:
        raise BusinessRuleError("project 분류체계는 project_id가 필요합니다.", status_code=422)


def _ensure_project_exists(db: Session, project_id: int) -> ContractPeriod:
    project = db.get(ContractPeriod, project_id)
    if project is None:
        raise NotFoundError("Project period not found")
    return project


def _ensure_scheme_name_unique(
    db: Session,
    scope_type: str,
    project_id: int | None,
    name: str,
    scheme_id: int | None = None,
) -> None:
    stmt = select(ClassificationScheme).where(
        ClassificationScheme.scope_type == scope_type,
        ClassificationScheme.project_id == project_id,
        ClassificationScheme.name == name,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if scheme_id is not None and existing.id == scheme_id:
        return
    raise DuplicateError("동일 범위에 같은 이름의 분류체계가 이미 존재합니다.")


def _ensure_node_code_unique(
    db: Session,
    scheme_id: int,
    node_code: str,
    node_id: int | None = None,
) -> None:
    stmt = select(ClassificationNode).where(
        ClassificationNode.scheme_id == scheme_id,
        ClassificationNode.node_code == node_code,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if node_id is not None and existing.id == node_id:
        return
    raise DuplicateError("같은 분류체계에 동일한 node_code가 이미 존재합니다.")


def _get_parent_node(
    db: Session,
    scheme_id: int,
    parent_id: int | None,
    node_id: int | None = None,
) -> ClassificationNode | None:
    if parent_id is None:
        return None
    parent = get_classification_node(db, parent_id)
    if parent.scheme_id != scheme_id:
        raise BusinessRuleError("다른 분류체계의 노드를 부모로 선택할 수 없습니다.", status_code=422)
    if node_id is not None and parent.id == node_id:
        raise BusinessRuleError("자기 자신을 부모로 선택할 수 없습니다.", status_code=422)
    return parent


def _normalize_asset_type_meta(
    asset_type_key: str | None,
    asset_type_code: str | None,
    asset_type_label: str | None,
    asset_kind: str | None,
    is_catalog_assignable: bool | None,
) -> dict[str, str | bool | None]:
    normalized = {
        "asset_type_key": (asset_type_key or "").strip() or None,
        "asset_type_code": ((asset_type_code or "").strip().upper()) or None,
        "asset_type_label": (asset_type_label or "").strip() or None,
        "asset_kind": (asset_kind or "").strip() or None,
        "is_catalog_assignable": bool(is_catalog_assignable),
    }
    populated_count = sum(
        1 for key in ("asset_type_key", "asset_type_code", "asset_type_label", "asset_kind")
        if normalized[key]
    )
    if populated_count and populated_count != 4:
        raise BusinessRuleError(
            "자산유형 통합 메타는 유형키, 코드, 표시명, kind를 함께 입력해야 합니다.",
            status_code=422,
        )
    if normalized["is_catalog_assignable"] and populated_count != 4:
        raise BusinessRuleError(
            "카탈로그 할당 가능 분류는 자산유형 통합 메타를 모두 가져야 합니다.",
            status_code=422,
        )
    if populated_count == 0:
        normalized["is_catalog_assignable"] = False
    return normalized

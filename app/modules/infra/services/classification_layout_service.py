from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth.authorization import can_manage_catalog_taxonomy
from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.user import User
from app.modules.infra.models.catalog_attribute_def import CatalogAttributeDef
from app.modules.infra.models.classification_layout import ClassificationLayout
from app.modules.infra.models.classification_layout_level import ClassificationLayoutLevel
from app.modules.infra.models.classification_layout_level_key import ClassificationLayoutLevelKey
from app.modules.infra.schemas.classification_layout import ClassificationLayoutCreate, ClassificationLayoutUpdate
from app.modules.infra.services.classification_identity_service import (
    PRIMARY_LAYOUT_ATTRIBUTE_KEYS,
    is_valid_primary_layout_attribute,
)


def list_layouts(
    db: Session,
    scope_type: str | None = None,
    project_id: int | None = None,
    active_only: bool = False,
) -> list[ClassificationLayout]:
    stmt = select(ClassificationLayout).order_by(
        ClassificationLayout.scope_type.asc(),
        ClassificationLayout.name.asc(),
        ClassificationLayout.id.asc(),
    )
    if scope_type:
        stmt = stmt.where(ClassificationLayout.scope_type == scope_type)
    if project_id is not None:
        stmt = stmt.where(ClassificationLayout.project_id == project_id)
    if active_only:
        stmt = stmt.where(ClassificationLayout.is_active.is_(True))
    return list(db.scalars(stmt))


def get_layout(db: Session, layout_id: int) -> ClassificationLayout:
    layout = db.scalar(
        select(ClassificationLayout)
        .options(
            selectinload(ClassificationLayout.levels).selectinload(ClassificationLayoutLevel.keys),
        )
        .where(ClassificationLayout.id == layout_id)
    )
    if layout is None:
        raise NotFoundError("분류 레이아웃을 찾을 수 없습니다.")
    return layout


def get_layout_detail(db: Session, layout_id: int) -> dict:
    layout = get_layout(db, layout_id)
    return {
        "id": layout.id,
        "scope_type": layout.scope_type,
        "project_id": layout.project_id,
        "name": layout.name,
        "description": layout.description,
        "depth_count": layout.depth_count,
        "is_default": layout.is_default,
        "is_active": layout.is_active,
        "levels": [
            {
                "id": level.id,
                "level_no": level.level_no,
                "alias": level.alias,
                "joiner": level.joiner,
                "prefix_mode": level.prefix_mode,
                "sort_order": level.sort_order,
                "keys": [
                    {
                        "id": key.id,
                        "attribute_id": key.attribute_id,
                        "attribute_key": key.attribute.attribute_key if key.attribute else None,
                        "sort_order": key.sort_order,
                        "is_visible": key.is_visible,
                    }
                    for key in sorted(level.keys, key=lambda item: (item.sort_order, item.id))
                ],
            }
            for level in sorted(layout.levels, key=lambda item: (item.level_no, item.id))
        ],
    }


def create_layout(
    db: Session,
    payload: ClassificationLayoutCreate,
    current_user: User,
) -> ClassificationLayout:
    _require_taxonomy_edit(current_user)
    _ensure_scope(payload.scope_type, payload.project_id)
    if db.scalar(
        select(ClassificationLayout).where(
            ClassificationLayout.scope_type == payload.scope_type,
            ClassificationLayout.project_id == payload.project_id,
            ClassificationLayout.name == payload.name,
        )
    ):
        raise DuplicateError("같은 범위에 동일한 레이아웃 이름이 이미 존재합니다.")
    _validate_layout_payload(db, payload, depth_count=payload.depth_count)
    layout = ClassificationLayout(
        scope_type=payload.scope_type,
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
        depth_count=payload.depth_count,
        is_default=payload.is_default,
        is_active=payload.is_active,
    )
    db.add(layout)
    db.flush()
    _replace_layout_levels(db, layout, payload.levels)
    db.commit()
    db.refresh(layout)
    return get_layout(db, layout.id)


def update_layout(
    db: Session,
    layout_id: int,
    payload: ClassificationLayoutUpdate,
    current_user: User,
) -> ClassificationLayout:
    _require_taxonomy_edit(current_user)
    layout = get_layout(db, layout_id)
    updates = payload.model_dump(exclude_unset=True, exclude={"levels"})
    next_depth = updates.get("depth_count", layout.depth_count)
    if "levels" in payload.model_fields_set:
        _validate_layout_payload(db, payload, depth_count=next_depth)
    for field, value in updates.items():
        setattr(layout, field, value)
    if payload.levels is not None:
        _replace_layout_levels(db, layout, payload.levels)
    db.commit()
    db.refresh(layout)
    return get_layout(db, layout.id)


def delete_layout(db: Session, layout_id: int, current_user: User) -> None:
    _require_taxonomy_edit(current_user)
    layout = get_layout(db, layout_id)
    in_use = db.scalar(
        select(ContractPeriod.id).where(ContractPeriod.classification_layout_id == layout_id).limit(1)
    )
    if in_use is not None:
        raise BusinessRuleError("프로젝트에 연결된 레이아웃은 삭제할 수 없습니다.")
    db.delete(layout)
    db.commit()


def assign_project_layout(
    db: Session,
    project_id: int,
    layout_id: int,
    current_user: User,
) -> None:
    _require_taxonomy_edit(current_user)
    project = _get_project(db, project_id)
    get_layout(db, layout_id)
    project.classification_layout_id = layout_id
    db.commit()


def get_project_layout(db: Session, project_id: int) -> ClassificationLayout | None:
    project = _get_project(db, project_id)
    if not project.classification_layout_id:
        return None
    return get_layout(db, project.classification_layout_id)


def _validate_layout_payload(
    db: Session,
    payload: ClassificationLayoutCreate | ClassificationLayoutUpdate,
    *,
    depth_count: int | None = None,
) -> None:
    levels = payload.levels
    if levels is None:
        return
    _validate_layout_levels(levels, expected_depth=depth_count)
    _validate_display_required_attributes(db, levels)


def _validate_layout_levels(levels: list, expected_depth: int | None = None) -> None:
    seen_levels: set[int] = set()
    seen_keys: set[str] = set()
    level_one_key: str | None = None
    disallowed_keys = {"vendor_series"}
    for level in levels:
        if level.level_no in seen_levels:
            raise BusinessRuleError("레이아웃 level 번호가 중복되었습니다.")
        seen_levels.add(level.level_no)
        if len(level.keys) != 1:
            raise BusinessRuleError("각 레벨에는 정확히 하나의 속성만 배치할 수 있습니다.")
        for key in level.keys:
            if key.attribute_key in disallowed_keys:
                raise BusinessRuleError("vendor_series는 분류 레이아웃 키로 사용할 수 없습니다.")
            if key.attribute_key in seen_keys:
                raise BusinessRuleError("같은 속성은 한 레이아웃에 한 번만 배치할 수 있습니다.")
            seen_keys.add(key.attribute_key)
            if level.level_no == 1:
                level_one_key = key.attribute_key
    if expected_depth is not None and len(levels) != expected_depth:
        raise BusinessRuleError("레이아웃 depth 수와 level 수가 일치해야 합니다.")
    if seen_keys.intersection({"domain", "imp_type"}) != {"domain", "imp_type"}:
        raise BusinessRuleError("레이아웃에는 domain과 imp_type가 각각 정확히 1회 포함되어야 합니다.")
    if not is_valid_primary_layout_attribute(level_one_key):
        allowed = ", ".join(sorted(PRIMARY_LAYOUT_ATTRIBUTE_KEYS))
        raise BusinessRuleError(f"level 1에는 {allowed} 중 하나만 배치할 수 있습니다.")


def _validate_display_required_attributes(db: Session, levels: list) -> None:
    required_keys = set(
        db.scalars(
            select(CatalogAttributeDef.attribute_key).where(
                CatalogAttributeDef.is_active.is_(True),
                CatalogAttributeDef.is_display_required.is_(True),
            )
        )
    )
    if not required_keys:
        return
    included = {key.attribute_key for level in levels for key in level.keys}
    missing = sorted(required_keys - included)
    if missing:
        raise BusinessRuleError(f"레이아웃에 필수 표시 속성이 누락되었습니다: {', '.join(missing)}")


def _replace_layout_levels(db: Session, layout: ClassificationLayout, levels: list) -> None:
    attribute_map = {
        item.attribute_key: item
        for item in db.scalars(select(CatalogAttributeDef).where(CatalogAttributeDef.is_active.is_(True)))
    }
    for existing in list(layout.levels):
        db.delete(existing)
    db.flush()
    for level_payload in levels:
        level = ClassificationLayoutLevel(
            layout_id=layout.id,
            level_no=level_payload.level_no,
            alias=level_payload.alias,
            joiner=level_payload.joiner,
            prefix_mode=level_payload.prefix_mode,
            sort_order=level_payload.sort_order,
        )
        db.add(level)
        db.flush()
        for key_payload in level_payload.keys:
            attribute = attribute_map.get(key_payload.attribute_key)
            if attribute is None:
                raise BusinessRuleError(f"존재하지 않거나 비활성화된 속성입니다: {key_payload.attribute_key}")
            db.add(
                ClassificationLayoutLevelKey(
                    level_id=level.id,
                    attribute_id=attribute.id,
                    sort_order=key_payload.sort_order,
                    is_visible=key_payload.is_visible,
                )
            )


def _ensure_scope(scope_type: str, project_id: int | None) -> None:
    if scope_type == "project" and project_id is None:
        raise BusinessRuleError("프로젝트 범위 레이아웃은 프로젝트 id가 필요합니다.")
    if scope_type == "global" and project_id is not None:
        raise BusinessRuleError("글로벌 레이아웃에는 프로젝트 id를 지정할 수 없습니다.")


def _require_taxonomy_edit(current_user: User) -> None:
    if not can_manage_catalog_taxonomy(current_user):
        raise PermissionDeniedError("카탈로그 기준 관리 권한이 필요합니다.")


def _get_project(db: Session, project_id: int) -> ContractPeriod:
    project = db.get(ContractPeriod, project_id)
    if project is None:
        raise NotFoundError("프로젝트를 찾을 수 없습니다.")
    return project

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth.authorization import can_manage_catalog_taxonomy
from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.user import User
from app.modules.infra.models.catalog_attribute_def import CatalogAttributeDef
from app.modules.infra.models.catalog_attribute_option import CatalogAttributeOption
from app.modules.infra.models.classification_layout_level_key import ClassificationLayoutLevelKey
from app.modules.infra.models.product_catalog_attribute_value import ProductCatalogAttributeValue
from app.modules.infra.schemas.catalog_attribute import CatalogAttributeCreate, CatalogAttributeUpdate
from app.modules.infra.schemas.catalog_attribute_option import (
    CatalogAttributeOptionCreate,
    CatalogAttributeOptionUpdate,
)
from app.modules.infra.models.catalog_attribute_option_alias import CatalogAttributeOptionAlias
from app.modules.infra.services.catalog_alias_service import normalize_catalog_alias, resolve_attribute_option_canonical


def list_attributes(db: Session, active_only: bool = False) -> list[CatalogAttributeDef]:
    stmt = select(CatalogAttributeDef).order_by(
        CatalogAttributeDef.sort_order.asc(),
        CatalogAttributeDef.id.asc(),
    )
    if active_only:
        stmt = stmt.where(CatalogAttributeDef.is_active.is_(True))
    return list(db.scalars(stmt))


def get_attribute(db: Session, attribute_id: int) -> CatalogAttributeDef:
    attribute = db.get(CatalogAttributeDef, attribute_id)
    if attribute is None:
        raise NotFoundError("속성을 찾을 수 없습니다.")
    return attribute


def create_attribute(
    db: Session,
    payload: CatalogAttributeCreate,
    current_user: User,
) -> CatalogAttributeDef:
    _require_taxonomy_edit(current_user)
    _validate_attribute_definition(payload)
    exists = db.scalar(
        select(CatalogAttributeDef).where(CatalogAttributeDef.attribute_key == payload.attribute_key)
    )
    if exists is not None:
        raise DuplicateError("같은 속성 키가 이미 존재합니다.")
    attribute = CatalogAttributeDef(**payload.model_dump())
    db.add(attribute)
    db.commit()
    db.refresh(attribute)
    return attribute


def update_attribute(
    db: Session,
    attribute_id: int,
    payload: CatalogAttributeUpdate,
    current_user: User,
) -> CatalogAttributeDef:
    _require_taxonomy_edit(current_user)
    attribute = get_attribute(db, attribute_id)
    _validate_attribute_definition(payload)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(attribute, field, value)
    db.commit()
    db.refresh(attribute)
    return attribute


def delete_attribute(db: Session, attribute_id: int, current_user: User) -> None:
    _require_taxonomy_edit(current_user)
    attribute = get_attribute(db, attribute_id)
    _guard_attribute_delete(db, attribute_id)
    db.delete(attribute)
    db.commit()


def list_attribute_options(
    db: Session,
    attribute_id: int,
    active_only: bool = False,
) -> list[CatalogAttributeOption]:
    get_attribute(db, attribute_id)
    stmt = (
        select(CatalogAttributeOption)
        .where(CatalogAttributeOption.attribute_id == attribute_id)
        .options(selectinload(CatalogAttributeOption.aliases))
        .order_by(CatalogAttributeOption.sort_order.asc(), CatalogAttributeOption.id.asc())
    )
    if active_only:
        stmt = stmt.where(CatalogAttributeOption.is_active.is_(True))
    options = list(db.scalars(stmt))
    for option in options:
        _enrich_option_scope(option)
    return options


def create_attribute_option(
    db: Session,
    attribute_id: int,
    payload: CatalogAttributeOptionCreate,
    current_user: User,
) -> CatalogAttributeOption:
    _require_taxonomy_edit(current_user)
    attribute = get_attribute(db, attribute_id)
    exists = db.scalar(
        select(CatalogAttributeOption).where(
            CatalogAttributeOption.attribute_id == attribute_id,
            CatalogAttributeOption.option_key == payload.option_key,
        )
    )
    if exists is not None:
        raise DuplicateError("같은 속성값 키가 이미 존재합니다.")
    payload_dict = payload.model_dump()
    payload_dict["domain_option_id"] = _validate_option_scope(
        db,
        attribute,
        option_key=payload.option_key,
        domain_option_id=payload.domain_option_id,
    )
    _guard_same_attribute_option_duplicate(db, attribute_id, payload.option_key, payload.label, label_kr=payload.label_kr)
    _guard_cross_attribute_option_duplicate(db, attribute_id, payload.option_key, payload.label, label_kr=payload.label_kr)
    option = CatalogAttributeOption(attribute_id=attribute_id, **payload_dict)
    db.add(option)
    db.flush()
    _sync_label_kr_auto_alias(db, option)
    db.commit()
    db.refresh(option)
    _enrich_option_scope(option)
    return option


def update_attribute_option(
    db: Session,
    option_id: int,
    payload: CatalogAttributeOptionUpdate,
    current_user: User,
) -> CatalogAttributeOption:
    _require_taxonomy_edit(current_user)
    option = _get_option(db, option_id)
    updates = payload.model_dump(exclude_unset=True)
    next_option_key = updates.get("option_key", option.option_key)
    next_label = updates.get("label", option.label)
    attribute = get_attribute(db, option.attribute_id)
    if next_option_key != option.option_key:
        exists = db.scalar(
            select(CatalogAttributeOption).where(
                CatalogAttributeOption.attribute_id == option.attribute_id,
                CatalogAttributeOption.option_key == next_option_key,
                CatalogAttributeOption.id != option.id,
            )
        )
        if exists is not None:
            raise DuplicateError("같은 속성값 키가 이미 존재합니다.")
    next_label_kr = updates.get("label_kr", option.label_kr)
    _guard_same_attribute_option_duplicate(
        db,
        option.attribute_id,
        next_option_key,
        next_label,
        label_kr=next_label_kr,
        exclude_option_id=option.id,
    )
    _guard_cross_attribute_option_duplicate(db, option.attribute_id, next_option_key, next_label, label_kr=next_label_kr, exclude_option_id=option.id)
    if "domain_option_id" in updates or attribute.attribute_key == "product_family":
        updates["domain_option_id"] = _validate_option_scope(
            db,
            attribute,
            option_key=next_option_key,
            domain_option_id=updates.get("domain_option_id", option.domain_option_id),
        )
    for field, value in updates.items():
        setattr(option, field, value)
    _sync_label_kr_auto_alias(db, option)
    db.commit()
    db.refresh(option)
    _enrich_option_scope(option)
    return option


def delete_attribute_option(db: Session, option_id: int, current_user: User) -> None:
    _require_taxonomy_edit(current_user)
    option = _get_option(db, option_id)
    _guard_option_delete(db, option_id)
    db.delete(option)
    db.commit()


def _sync_label_kr_auto_alias(db: Session, option: CatalogAttributeOption) -> None:
    """label_kr 변경 시 label_kr_auto alias를 동기화한다."""
    existing_auto = db.scalar(
        select(CatalogAttributeOptionAlias).where(
            CatalogAttributeOptionAlias.attribute_option_id == option.id,
            CatalogAttributeOptionAlias.match_type == "label_kr_auto",
        )
    )
    label_kr = (option.label_kr or "").strip()
    if not label_kr:
        if existing_auto:
            db.delete(existing_auto)
        return
    normalized = normalize_catalog_alias(label_kr)
    if existing_auto:
        existing_auto.alias_value = label_kr
        existing_auto.normalized_alias = normalized
    else:
        conflict = db.scalar(
            select(CatalogAttributeOptionAlias).where(
                CatalogAttributeOptionAlias.attribute_option_id == option.id,
                CatalogAttributeOptionAlias.normalized_alias == normalized,
            )
        )
        if conflict is None:
            db.add(CatalogAttributeOptionAlias(
                attribute_option_id=option.id,
                alias_value=label_kr,
                normalized_alias=normalized,
                match_type="label_kr_auto",
            ))
    db.flush()


def _require_taxonomy_edit(current_user: User) -> None:
    if not can_manage_catalog_taxonomy(current_user):
        raise PermissionDeniedError("카탈로그 기준 관리 권한이 필요합니다.")


def _validate_attribute_definition(payload: CatalogAttributeCreate | CatalogAttributeUpdate) -> None:
    if getattr(payload, "is_display_required", None) and getattr(payload, "is_displayable", True) is False:
        raise BusinessRuleError("표시 필수 속성은 표시 가능해야 합니다.")
    if getattr(payload, "multi_value", None):
        raise BusinessRuleError("다중값 속성은 아직 지원하지 않습니다.")
    value_type = getattr(payload, "value_type", None)
    if value_type is not None and value_type not in {"option", "text"}:
        raise BusinessRuleError("지원하지 않는 속성 값 타입입니다.")


def _guard_attribute_delete(db: Session, attribute_id: int) -> None:
    in_values = db.scalar(
        select(ProductCatalogAttributeValue.id).where(ProductCatalogAttributeValue.attribute_id == attribute_id).limit(1)
    )
    if in_values is not None:
        raise BusinessRuleError("제품에 이미 사용 중인 속성은 삭제할 수 없습니다.")
    in_layout = db.scalar(
        select(ClassificationLayoutLevelKey.id).where(ClassificationLayoutLevelKey.attribute_id == attribute_id).limit(1)
    )
    if in_layout is not None:
        raise BusinessRuleError("레이아웃에 배치된 속성은 삭제할 수 없습니다.")


def _guard_option_delete(db: Session, option_id: int) -> None:
    in_values = db.scalar(
        select(ProductCatalogAttributeValue.id).where(ProductCatalogAttributeValue.option_id == option_id).limit(1)
    )
    if in_values is not None:
        raise BusinessRuleError("제품에 이미 사용 중인 속성값은 삭제할 수 없습니다.")


def _get_option(db: Session, option_id: int) -> CatalogAttributeOption:
    option = db.scalars(
        select(CatalogAttributeOption)
        .where(CatalogAttributeOption.id == option_id)
        .options(selectinload(CatalogAttributeOption.aliases))
    ).first()
    if option is None:
        raise NotFoundError("속성값을 찾을 수 없습니다.")
    _enrich_option_scope(option)
    return option


def _guard_cross_attribute_option_duplicate(
    db: Session,
    attribute_id: int,
    option_key: str,
    label: str,
    *,
    label_kr: str | None = None,
    exclude_option_id: int | None = None,
) -> None:
    layout_attribute_ids = set(
        db.scalars(select(ClassificationLayoutLevelKey.attribute_id).distinct())
    )
    if not layout_attribute_ids:
        return
    if attribute_id not in layout_attribute_ids:
        return
    sibling_attribute_ids = layout_attribute_ids - {attribute_id}
    if not sibling_attribute_ids:
        return
    candidates = list(
        db.scalars(
            select(CatalogAttributeOption).where(
                CatalogAttributeOption.attribute_id.in_(sibling_attribute_ids),
            )
        )
    )
    normalized_key = option_key.strip().lower()
    normalized_label = label.strip().casefold()
    for candidate in candidates:
        if exclude_option_id and candidate.id == exclude_option_id:
            continue
        if StringOrEmpty(candidate.option_key).lower() == normalized_key:
            raise DuplicateError("다른 depth에 이미 같은 속성값 키가 존재합니다.")
        if StringOrEmpty(candidate.label).casefold() == normalized_label:
            raise DuplicateError("다른 depth에 이미 같은 아이템명이 존재합니다.")
    if label_kr:
        normalized_label_kr = label_kr.strip().casefold()
        for candidate in candidates:
            if exclude_option_id and candidate.id == exclude_option_id:
                continue
            if candidate.label_kr and StringOrEmpty(candidate.label_kr).casefold() == normalized_label_kr:
                raise DuplicateError("다른 depth에 이미 같은 한글 아이템명이 존재합니다.")


def StringOrEmpty(value: str | None) -> str:
    return value or ""


def _guard_same_attribute_option_duplicate(
    db: Session,
    attribute_id: int,
    option_key: str,
    label: str,
    *,
    label_kr: str | None = None,
    exclude_option_id: int | None = None,
) -> None:
    candidates = list(
        db.scalars(
            select(CatalogAttributeOption).where(
                CatalogAttributeOption.attribute_id == attribute_id,
            )
        )
    )
    normalized_key = option_key.strip().lower()
    normalized_label = label.strip().casefold()
    for candidate in candidates:
        if exclude_option_id and candidate.id == exclude_option_id:
            continue
        if StringOrEmpty(candidate.option_key).lower() == normalized_key:
            raise DuplicateError("같은 속성값 키가 이미 존재합니다.")
        if StringOrEmpty(candidate.label).casefold() == normalized_label:
            raise DuplicateError("같은 아이템명이 이미 존재합니다.")
    if label_kr:
        normalized_label_kr = label_kr.strip().casefold()
        for candidate in candidates:
            if exclude_option_id and candidate.id == exclude_option_id:
                continue
            if candidate.label_kr and StringOrEmpty(candidate.label_kr).casefold() == normalized_label_kr:
                raise DuplicateError("같은 한글 아이템명이 이미 존재합니다.")


def resolve_attribute_option_or_raise(
    db: Session,
    attribute_key: str,
    option_key: str | None,
    raw_value: str | None = None,
) -> tuple[CatalogAttributeDef, CatalogAttributeOption | None]:
    attribute = db.scalar(
        select(CatalogAttributeDef).where(
            CatalogAttributeDef.attribute_key == attribute_key,
            CatalogAttributeDef.is_active.is_(True),
        )
    )
    if attribute is None:
        raise BusinessRuleError(f"존재하지 않거나 비활성화된 속성입니다: {attribute_key}")
    if attribute.value_type != "option":
        return attribute, None
    option = resolve_attribute_option_canonical(
        db,
        attribute_key=attribute_key,
        option_key=option_key,
        raw_value=raw_value,
    )
    if option is None:
        lookup_value = option_key or raw_value or ""
        raise BusinessRuleError(f"속성값을 찾을 수 없습니다: {attribute_key}.{lookup_value}")
    return attribute, option


def _validate_option_scope(
    db: Session,
    attribute: CatalogAttributeDef,
    *,
    option_key: str | None,
    domain_option_id: int | None,
) -> int | None:
    if attribute.attribute_key != "product_family":
        return None
    normalized_option_key = (option_key or "").strip().lower()
    if domain_option_id is None:
        if normalized_option_key == "generic":
            return None
        raise BusinessRuleError("제품군 아이템에는 도메인 지정이 필요합니다.")
    domain_attribute = db.scalar(
        select(CatalogAttributeDef).where(CatalogAttributeDef.attribute_key == "domain")
    )
    if domain_attribute is None:
        raise BusinessRuleError("도메인 속성을 찾을 수 없습니다.")
    domain_option = db.get(CatalogAttributeOption, domain_option_id)
    if domain_option is None or domain_option.attribute_id != domain_attribute.id:
        raise BusinessRuleError("유효한 도메인 아이템을 선택하세요.")
    return domain_option.id


def _enrich_option_scope(option: CatalogAttributeOption) -> None:
    domain_option = getattr(option, "domain_option", None)
    option.domain_option_key = domain_option.option_key if domain_option is not None else None
    option.domain_option_label = domain_option.label if domain_option is not None else None
    option.domain_option_label_kr = domain_option.label_kr if domain_option is not None else None

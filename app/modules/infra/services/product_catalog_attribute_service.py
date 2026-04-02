from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_manage_catalog_products
from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.modules.common.models.user import User
from app.modules.infra.models.catalog_attribute_def import CatalogAttributeDef
from app.modules.infra.models.catalog_attribute_option import CatalogAttributeOption
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.product_catalog_attribute_value import ProductCatalogAttributeValue
from app.modules.infra.services.catalog_attribute_service import resolve_attribute_option_or_raise
from app.modules.infra.schemas.product_catalog_attribute_value import ProductCatalogAttributesUpdate


def get_product_attributes(db: Session, product_id: int) -> list[dict]:
    product = _get_product(db, product_id)
    values = list(
        db.scalars(
            select(ProductCatalogAttributeValue)
            .where(ProductCatalogAttributeValue.product_id == product.id)
            .order_by(ProductCatalogAttributeValue.attribute_id.asc(), ProductCatalogAttributeValue.id.asc())
        )
    )
    attribute_ids = {item.attribute_id for item in values}
    option_ids = {item.option_id for item in values if item.option_id is not None}
    attributes = {
        item.id: item
        for item in db.scalars(select(CatalogAttributeDef).where(CatalogAttributeDef.id.in_(attribute_ids)))
    }
    options = {
        item.id: item
        for item in db.scalars(select(CatalogAttributeOption).where(CatalogAttributeOption.id.in_(option_ids)))
    }
    return [
        {
            "id": value.id,
            "product_id": value.product_id,
            "attribute_id": value.attribute_id,
            "option_id": value.option_id,
            "raw_value": value.raw_value,
            "sort_order": value.sort_order,
            "is_primary": value.is_primary,
            "attribute_key": attributes[value.attribute_id].attribute_key if value.attribute_id in attributes else None,
            "attribute_label": attributes[value.attribute_id].label if value.attribute_id in attributes else None,
            "option_key": options[value.option_id].option_key if value.option_id in options else None,
            "option_label": options[value.option_id].label if value.option_id in options else None,
            "option_label_kr": options[value.option_id].label_kr if value.option_id in options else None,
        }
        for value in values
    ]


def replace_product_attributes(
    db: Session,
    product_id: int,
    payload: ProductCatalogAttributesUpdate,
    current_user: User,
) -> list[dict]:
    _require_product_edit(current_user)
    product = _get_product(db, product_id)
    _validate_product_attribute_payload(db, payload)
    _ensure_required_attributes_present(db, payload)

    existing = list(
        db.scalars(select(ProductCatalogAttributeValue).where(ProductCatalogAttributeValue.product_id == product.id))
    )
    for item in existing:
        db.delete(item)
    db.flush()

    for entry in payload.attributes:
        attribute, option = _resolve_attribute_and_option(db, entry.attribute_key, entry.option_key, entry.raw_value)
        db.add(
            ProductCatalogAttributeValue(
                product_id=product.id,
                attribute_id=attribute.id,
                option_id=option.id if option else None,
                raw_value=entry.raw_value,
            )
        )
    db.commit()
    return get_product_attributes(db, product.id)


def _validate_product_attribute_payload(db: Session, payload: ProductCatalogAttributesUpdate) -> None:
    seen: set[str] = set()
    resolved: dict[str, tuple[CatalogAttributeDef, CatalogAttributeOption | None]] = {}
    for entry in payload.attributes:
        if entry.attribute_key in seen:
            raise BusinessRuleError(f"속성이 중복되었습니다: {entry.attribute_key}")
        seen.add(entry.attribute_key)
        attribute, option = _resolve_attribute_and_option(db, entry.attribute_key, entry.option_key, entry.raw_value)
        resolved[entry.attribute_key] = (attribute, option)
        if attribute.value_type == "option" and option is None:
            raise BusinessRuleError(f"옵션형 속성은 option_key가 필요합니다: {entry.attribute_key}")
        if attribute.value_type == "text" and not (entry.raw_value or "").strip():
            raise BusinessRuleError(f"텍스트형 속성은 raw_value가 필요합니다: {entry.attribute_key}")
    domain_option = resolved.get("domain", (None, None))[1]
    product_family_option = resolved.get("product_family", (None, None))[1]
    if product_family_option is not None and product_family_option.domain_option_id is not None:
        if domain_option is None or product_family_option.domain_option_id != domain_option.id:
            raise BusinessRuleError("선택한 제품군은 현재 도메인에 속하지 않습니다.")


def _ensure_required_attributes_present(db: Session, payload: ProductCatalogAttributesUpdate) -> None:
    required = set(
        db.scalars(
            select(CatalogAttributeDef.attribute_key).where(
                CatalogAttributeDef.is_active.is_(True),
                CatalogAttributeDef.is_required.is_(True),
            )
        )
    )
    provided = {entry.attribute_key for entry in payload.attributes}
    missing = sorted(required - provided)
    if missing:
        raise BusinessRuleError(f"필수 속성이 누락되었습니다: {', '.join(missing)}")


def _resolve_attribute_and_option(
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
    if attribute.value_type != "option" and option_key is None:
        return attribute, None
    return resolve_attribute_option_or_raise(db, attribute_key, option_key, raw_value)


def _require_product_edit(current_user: User) -> None:
    if not can_manage_catalog_products(current_user):
        raise PermissionDeniedError("카탈로그 제품 관리 권한이 필요합니다.")


def _get_product(db: Session, product_id: int) -> ProductCatalog:
    product = db.get(ProductCatalog, product_id)
    if product is None:
        raise NotFoundError("제품을 찾을 수 없습니다.")
    return product

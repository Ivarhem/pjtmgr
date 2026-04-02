from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.auth.authorization import can_manage_catalog_products
from app.modules.common.models.user import User
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.catalog_attribute_def import CatalogAttributeDef
from app.modules.infra.models.catalog_attribute_option import CatalogAttributeOption
from app.modules.infra.models.classification_layout import ClassificationLayout
from app.modules.infra.models.classification_layout_level import ClassificationLayoutLevel
from app.modules.infra.models.classification_layout_level_key import ClassificationLayoutLevelKey
from app.modules.infra.models.product_catalog_attribute_value import ProductCatalogAttributeValue
from app.modules.infra.models.hardware_spec import HardwareSpec
from app.modules.infra.models.software_spec import SoftwareSpec
from app.modules.infra.models.model_spec import ModelSpec
from app.modules.infra.models.generic_catalog_profile import GenericCatalogProfile
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.models.product_catalog_list_cache import ProductCatalogListCache
from app.modules.infra.schemas.product_catalog import (
    ProductCatalogBulkUpsertRow,
    ProductCatalogCreate,
    ProductCatalogUpdate,
)
from app.modules.infra.schemas.hardware_spec import HardwareSpecCreate, HardwareSpecUpdate
from app.modules.infra.schemas.software_spec import SoftwareSpecCreate, SoftwareSpecUpdate
from app.modules.infra.schemas.model_spec import ModelSpecCreate, ModelSpecUpdate
from app.modules.infra.schemas.generic_catalog_profile import (
    GenericCatalogProfileCreate,
    GenericCatalogProfileUpdate,
)
from app.modules.infra.schemas.hardware_interface import (
    HardwareInterfaceCreate,
    HardwareInterfaceUpdate,
)
from app.modules.infra.schemas.product_catalog_attribute_value import ProductCatalogAttributesUpdate
from app.modules.infra.services.catalog_alias_service import resolve_vendor_canonical
from app.modules.infra.services.catalog_similarity_service import build_normalized_catalog_fields
from app.modules.infra.services.product_catalog_attribute_service import (
    get_product_attributes,
    replace_product_attributes,
)


# ── ProductCatalog CRUD ──


def list_products(
    db: Session,
    vendor: str | None = None,
    product_type: str | None = None,
    q: str | None = None,
) -> list[dict]:
    layout_id = _get_default_layout_id(db)

    cached = _read_product_list_cache(db, layout_id, vendor, product_type, q)
    if cached is not None:
        return cached

    # Cache miss — compute via bulk, populate cache, return
    stmt = select(ProductCatalog).order_by(
        ProductCatalog.vendor.asc(), ProductCatalog.name.asc()
    )
    if vendor is not None:
        stmt = stmt.where(ProductCatalog.vendor == vendor)
    if product_type is not None:
        stmt = stmt.where(ProductCatalog.product_type == product_type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(ProductCatalog.name.ilike(like), ProductCatalog.vendor.ilike(like))
        )
    rows = list(db.scalars(stmt))
    results = _serialize_products_bulk(db, rows)

    # Populate cache (all products, not just filtered)
    _populate_product_list_cache(db, layout_id)

    return results


def get_product(db: Session, product_id: int) -> ProductCatalog:
    product = db.get(ProductCatalog, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    return product


def get_product_detail(db: Session, product_id: int) -> dict:
    """제품 상세 조회 (spec + interfaces 포함)."""
    product = get_product(db, product_id)
    hardware_spec = db.scalar(
        select(HardwareSpec).where(HardwareSpec.product_id == product_id)
    )
    software_spec = db.scalar(
        select(SoftwareSpec).where(SoftwareSpec.product_id == product_id)
    )
    model_spec = db.scalar(
        select(ModelSpec).where(ModelSpec.product_id == product_id)
    )
    generic_profile = db.scalar(
        select(GenericCatalogProfile).where(GenericCatalogProfile.product_id == product_id)
    )
    interfaces = list(
        db.scalars(
            select(HardwareInterface)
            .where(HardwareInterface.product_id == product_id)
            .order_by(HardwareInterface.id.asc())
        )
    )
    result = _serialize_product(db, product)
    result["hardware_spec"] = hardware_spec
    result["software_spec"] = software_spec
    result["model_spec"] = model_spec
    result["generic_profile"] = generic_profile
    result["interfaces"] = interfaces
    return result


def create_product(
    db: Session, payload: ProductCatalogCreate, current_user: User
) -> ProductCatalog:
    _require_edit(current_user)
    payload.vendor = resolve_vendor_canonical(db, payload.vendor) or payload.vendor
    _ensure_vendor_name_unique(db, payload.vendor, payload.name)
    attribute_payload = _resolve_product_attribute_payload(payload)
    product = ProductCatalog(
        **payload.model_dump(exclude={"product_type", "attributes"}),
        product_type=payload.product_type,
        **build_normalized_catalog_fields(payload.vendor, payload.name),
    )
    db.add(product)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="product_catalog",
        entity_id=None, summary=f"제품 등록: {product.vendor} {product.name}",
        module="infra",
    )
    db.commit()
    db.refresh(product)
    if attribute_payload is not None:
        replace_product_attributes(db, product.id, attribute_payload, current_user)
    invalidate_product_list_cache(db, product.id)
    return _serialize_product(db, product)


def update_product(
    db: Session, product_id: int, payload: ProductCatalogUpdate, current_user: User
) -> ProductCatalog:
    _require_edit(current_user)
    product = get_product(db, product_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"attributes"})
    if "vendor" in changes:
        changes["vendor"] = resolve_vendor_canonical(db, changes.get("vendor")) or changes.get("vendor")

    new_vendor = changes.get("vendor", product.vendor)
    new_name = changes.get("name", product.name)
    if new_vendor != product.vendor or new_name != product.name:
        _ensure_vendor_name_unique(db, new_vendor, new_name, product_id)
    attribute_payload = _resolve_product_attribute_payload(payload, product=product)

    for field, value in changes.items():
        setattr(product, field, value)
    if "vendor" in changes or "name" in changes:
        normalized = build_normalized_catalog_fields(new_vendor, new_name)
        product.normalized_vendor = normalized["normalized_vendor"]
        product.normalized_name = normalized["normalized_name"]

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="product_catalog",
        entity_id=product.id, summary=f"제품 수정: {product.vendor} {product.name}",
        module="infra",
    )
    db.commit()
    db.refresh(product)
    if attribute_payload is not None:
        replace_product_attributes(db, product.id, attribute_payload, current_user)
    invalidate_product_list_cache(db, product.id)
    return _serialize_product(db, product)


def delete_product(db: Session, product_id: int, current_user: User) -> None:
    _require_edit(current_user)
    product = get_product(db, product_id)

    if product.is_placeholder:
        raise BusinessRuleError(
            "시스템 placeholder 항목은 삭제할 수 없습니다.", status_code=403
        )
    _guard_asset_references(db, product_id)

    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="product_catalog",
        entity_id=product.id, summary=f"제품 삭제: {product.vendor} {product.name}",
        module="infra",
    )
    db.delete(product)
    db.commit()
    invalidate_product_list_cache(db, product_id)


def bulk_upsert_products(
    db: Session,
    rows: list[ProductCatalogBulkUpsertRow],
    current_user: User,
) -> dict:
    _require_edit(current_user)
    created = 0
    updated = 0
    failed = 0
    results: list[dict] = []

    for index, row in enumerate(rows, start=1):
        try:
            existing = None
            if row.product_id:
                existing = db.get(ProductCatalog, row.product_id)
                if existing is None:
                    raise NotFoundError("수정 대상 제품을 찾을 수 없습니다.")
            else:
                normalized_vendor = resolve_vendor_canonical(db, row.vendor) or row.vendor
                existing = db.scalar(
                    select(ProductCatalog).where(
                        ProductCatalog.vendor == normalized_vendor,
                        ProductCatalog.name == row.name,
                    )
                )

            payload = _build_bulk_upsert_payload(row)
            if existing is None:
                saved = create_product(db, ProductCatalogCreate(**payload), current_user)
                created += 1
                action = "created"
            else:
                saved = update_product(db, existing.id, ProductCatalogUpdate(**payload), current_user)
                updated += 1
                action = "updated"
            results.append(
                {
                    "row_no": index,
                    "action": action,
                    "product_id": saved["id"],
                    "vendor": saved["vendor"],
                    "name": saved["name"],
                    "status": "ok",
                    "message": None,
                }
            )
        except Exception as exc:
            db.rollback()
            failed += 1
            results.append(
                {
                    "row_no": index,
                    "action": "failed",
                    "product_id": row.product_id,
                    "vendor": row.vendor,
                    "name": row.name,
                    "status": "error",
                    "message": str(exc),
                }
            )

    return {
        "total": len(rows),
        "created": created,
        "updated": updated,
        "failed": failed,
        "rows": results,
    }


# ── HardwareSpec (1:1 sub-resource) ──


def upsert_spec(
    db: Session, product_id: int, payload: HardwareSpecCreate | HardwareSpecUpdate,
    current_user: User,
) -> HardwareSpec:
    _require_edit(current_user)
    product = get_product(db, product_id)

    spec = db.scalar(
        select(HardwareSpec).where(HardwareSpec.product_id == product_id)
    )
    data = payload.model_dump(exclude_unset=True)

    if spec is None:
        spec = HardwareSpec(product_id=product_id, **data)
        db.add(spec)
    else:
        for field, value in data.items():
            setattr(spec, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="hardware_spec",
        entity_id=product.id,
        summary=f"HW 스펙 갱신: {product.vendor} {product.name}", module="infra",
    )
    db.commit()
    db.refresh(spec)
    return spec


def upsert_software_spec(
    db: Session, product_id: int, payload: SoftwareSpecCreate | SoftwareSpecUpdate,
    current_user: User,
) -> SoftwareSpec:
    _require_edit(current_user)
    product = get_product(db, product_id)
    if product.product_type != "software":
        raise BusinessRuleError("소프트웨어 제품에서만 저장할 수 있습니다.", status_code=409)

    spec = db.scalar(
        select(SoftwareSpec).where(SoftwareSpec.product_id == product_id)
    )
    data = payload.model_dump(exclude_unset=True)

    if spec is None:
        spec = SoftwareSpec(product_id=product_id, **data)
        db.add(spec)
    else:
        for field, value in data.items():
            setattr(spec, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="software_spec",
        entity_id=product.id,
        summary=f"SW 스펙 갱신: {product.vendor} {product.name}", module="infra",
    )
    db.commit()
    db.refresh(spec)
    return spec


def upsert_model_spec(
    db: Session, product_id: int, payload: ModelSpecCreate | ModelSpecUpdate,
    current_user: User,
) -> ModelSpec:
    _require_edit(current_user)
    product = get_product(db, product_id)
    if product.product_type != "model":
        raise BusinessRuleError("모델 제품에서만 저장할 수 있습니다.", status_code=409)

    spec = db.scalar(
        select(ModelSpec).where(ModelSpec.product_id == product_id)
    )
    data = payload.model_dump(exclude_unset=True)

    if spec is None:
        spec = ModelSpec(product_id=product_id, **data)
        db.add(spec)
    else:
        for field, value in data.items():
            setattr(spec, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="model_spec",
        entity_id=product.id,
        summary=f"모델 스펙 갱신: {product.vendor} {product.name}", module="infra",
    )
    db.commit()
    db.refresh(spec)
    return spec


def upsert_generic_profile(
    db: Session,
    product_id: int,
    payload: GenericCatalogProfileCreate | GenericCatalogProfileUpdate,
    current_user: User,
) -> GenericCatalogProfile:
    _require_edit(current_user)
    product = get_product(db, product_id)
    if product.product_type not in {"service", "business_capability", "dataset"}:
        raise BusinessRuleError("해당 분류에서는 공통 프로필을 저장할 수 없습니다.", status_code=409)

    profile = db.scalar(
        select(GenericCatalogProfile).where(GenericCatalogProfile.product_id == product_id)
    )
    data = payload.model_dump(exclude_unset=True)

    if profile is None:
        profile = GenericCatalogProfile(product_id=product_id, **data)
        db.add(profile)
    else:
        for field, value in data.items():
            setattr(profile, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="generic_catalog_profile",
        entity_id=product.id,
        summary=f"공통 프로필 갱신: {product.vendor} {product.name}", module="infra",
    )
    db.commit()
    db.refresh(profile)
    return profile


# ── HardwareInterface (1:N sub-resource) ──


def list_interfaces(db: Session, product_id: int) -> list[HardwareInterface]:
    get_product(db, product_id)  # ensure exists
    return list(
        db.scalars(
            select(HardwareInterface)
            .where(HardwareInterface.product_id == product_id)
            .order_by(HardwareInterface.id.asc())
        )
    )


def create_interface(
    db: Session, product_id: int, payload: HardwareInterfaceCreate, current_user: User
) -> HardwareInterface:
    _require_edit(current_user)
    product = get_product(db, product_id)

    iface = HardwareInterface(product_id=product_id, **payload.model_dump())
    db.add(iface)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="hardware_interface",
        entity_id=product.id,
        summary=f"인터페이스 추가: {product.vendor} {product.name} - {iface.interface_type}",
        module="infra",
    )
    db.commit()
    db.refresh(iface)
    return iface


def update_interface(
    db: Session, product_id: int, interface_id: int,
    payload: HardwareInterfaceUpdate, current_user: User,
) -> HardwareInterface:
    _require_edit(current_user)
    get_product(db, product_id)

    iface = db.get(HardwareInterface, interface_id)
    if iface is None or iface.product_id != product_id:
        raise NotFoundError("Interface not found")

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(iface, field, value)

    db.commit()
    db.refresh(iface)
    return iface


def delete_interface(
    db: Session, product_id: int, interface_id: int, current_user: User
) -> None:
    _require_edit(current_user)
    get_product(db, product_id)

    iface = db.get(HardwareInterface, interface_id)
    if iface is None or iface.product_id != product_id:
        raise NotFoundError("Interface not found")

    db.delete(iface)
    db.commit()


# ── Cache helpers ──


def _get_default_layout_id(db: Session) -> int | None:
    layout = db.scalar(
        select(ClassificationLayout.id).where(
            ClassificationLayout.scope_type == "global",
            ClassificationLayout.is_active.is_(True),
            ClassificationLayout.is_default.is_(True),
        ).order_by(ClassificationLayout.id.asc())
    )
    return layout


def _read_product_list_cache(
    db: Session,
    layout_id: int | None,
    vendor: str | None = None,
    product_type: str | None = None,
    q: str | None = None,
) -> list[dict] | None:
    """캐시에서 제품 목록 조회. 캐시 미스 시 None 반환."""
    cache_count = db.scalar(
        select(func.count(ProductCatalogListCache.product_id)).where(
            ProductCatalogListCache.layout_id == layout_id
        )
    )
    if not cache_count:
        return None

    stmt = (
        select(ProductCatalogListCache.data)
        .join(ProductCatalog, ProductCatalog.id == ProductCatalogListCache.product_id)
        .where(ProductCatalogListCache.layout_id == layout_id)
        .order_by(ProductCatalog.vendor.asc(), ProductCatalog.name.asc())
    )
    if vendor is not None:
        stmt = stmt.where(ProductCatalog.vendor == vendor)
    if product_type is not None:
        stmt = stmt.where(ProductCatalog.product_type == product_type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(ProductCatalog.name.ilike(like), ProductCatalog.vendor.ilike(like))
        )
    return [row for row in db.scalars(stmt)]


def _populate_product_list_cache(db: Session, layout_id: int | None) -> None:
    """전체 제품의 캐시를 재구축한다."""
    all_products = list(
        db.scalars(
            select(ProductCatalog).order_by(
                ProductCatalog.vendor.asc(), ProductCatalog.name.asc()
            )
        )
    )
    all_data = _serialize_products_bulk(db, all_products)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Clear existing cache for this layout
    db.execute(
        delete(ProductCatalogListCache).where(
            ProductCatalogListCache.layout_id == layout_id
        )
    )

    # Insert all
    for product, data in zip(all_products, all_data):
        db.add(
            ProductCatalogListCache(
                product_id=product.id,
                layout_id=layout_id,
                data=data,
                cached_at=now,
            )
        )
    db.commit()


def invalidate_product_list_cache(
    db: Session, product_id: int | None = None
) -> None:
    """캐시 무효화. product_id가 주어지면 해당 제품만, 아니면 전체."""
    if product_id is not None:
        db.execute(
            delete(ProductCatalogListCache).where(
                ProductCatalogListCache.product_id == product_id
            )
        )
    else:
        db.execute(delete(ProductCatalogListCache))
    db.commit()


# ── Private helpers ──


def _guard_asset_references(db: Session, product_id: int) -> None:
    from app.modules.infra.models.asset import Asset
    count = db.scalar(
        select(Asset.id).where(Asset.hardware_model_id == product_id).limit(1)
    )
    if count is not None:
        raise BusinessRuleError(
            "이 제품을 참조하는 자산이 존재하여 삭제할 수 없습니다", status_code=409
        )


def _require_edit(current_user: User) -> None:
    if not can_manage_catalog_products(current_user):
        raise PermissionDeniedError("카탈로그 제품 수정 권한이 없습니다.")


def _ensure_vendor_name_unique(
    db: Session, vendor: str, name: str, product_id: int | None = None
) -> None:
    stmt = select(ProductCatalog).where(
        ProductCatalog.vendor == vendor, ProductCatalog.name == name
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if product_id is not None and existing.id == product_id:
        return
    raise DuplicateError("같은 제조사/모델명 조합이 이미 존재합니다")


def _serialize_product(db: Session, product: ProductCatalog) -> dict:
    result = {c.key: getattr(product, c.key) for c in product.__table__.columns}
    result["attributes"] = get_product_attributes(db, product.id)
    classification_meta = _get_product_classification_meta(db, product)
    result["classification_level_1_name"] = classification_meta["levels"][0]
    result["classification_level_2_name"] = classification_meta["levels"][1]
    result["classification_level_3_name"] = classification_meta["levels"][2]
    result["classification_level_4_name"] = classification_meta["levels"][3]
    result["classification_level_5_name"] = classification_meta["levels"][4]
    return result


def _serialize_products_bulk(db: Session, products: list[ProductCatalog]) -> list[dict]:
    """list_products 전용 벌크 직렬화. N+1 쿼리를 제거한다."""
    if not products:
        return []

    product_ids = [p.id for p in products]
    product_columns = ProductCatalog.__table__.columns

    # 1) 속성값 전체를 한 번에 로드
    all_values = list(
        db.scalars(
            select(ProductCatalogAttributeValue)
            .where(ProductCatalogAttributeValue.product_id.in_(product_ids))
            .order_by(
                ProductCatalogAttributeValue.product_id.asc(),
                ProductCatalogAttributeValue.attribute_id.asc(),
            )
        )
    )

    # 2) 참조 테이블 벌크 로드 (속성 정의 + 옵션 — 전체 로드, 소량 테이블)
    all_attr_defs = {
        a.id: a for a in db.scalars(select(CatalogAttributeDef))
    }
    attr_key_by_id = {a_id: a.attribute_key for a_id, a in all_attr_defs.items()}

    all_options = {
        o.id: o for o in db.scalars(select(CatalogAttributeOption))
    }

    # 3) product_id → attributes 맵 구축
    values_by_product: dict[int, list[dict]] = {pid: [] for pid in product_ids}
    for v in all_values:
        attr = all_attr_defs.get(v.attribute_id)
        opt = all_options.get(v.option_id) if v.option_id else None
        values_by_product[v.product_id].append({
            "id": v.id,
            "product_id": v.product_id,
            "attribute_id": v.attribute_id,
            "option_id": v.option_id,
            "raw_value": v.raw_value,
            "sort_order": v.sort_order,
            "is_primary": v.is_primary,
            "attribute_key": attr.attribute_key if attr else None,
            "attribute_label": attr.label if attr else None,
            "option_key": opt.option_key if opt else None,
            "option_label": opt.label if opt else None,
        })

    # 4) 레이아웃 한 번만 로드
    layout = db.scalar(
        select(ClassificationLayout)
        .options(
            selectinload(ClassificationLayout.levels)
            .selectinload(ClassificationLayoutLevel.keys)
            .selectinload(ClassificationLayoutLevelKey.attribute)
        )
        .where(
            ClassificationLayout.scope_type == "global",
            ClassificationLayout.is_active.is_(True),
            ClassificationLayout.is_default.is_(True),
        )
        .order_by(ClassificationLayout.id.asc())
    )

    # 5) 제품별 직렬화 (추가 DB 쿼리 없음)
    results: list[dict] = []
    for product in products:
        result = {c.key: getattr(product, c.key) for c in product_columns}
        attrs_list = values_by_product.get(product.id, [])
        result["attributes"] = attrs_list

        # 분류 레벨 계산
        attr_map = {
            a["attribute_key"]: {
                "option_key": a.get("option_key"),
                "label": a.get("option_label") or a.get("option_key") or a.get("raw_value"),
            }
            for a in attrs_list
            if a.get("attribute_key")
        }
        levels = _compute_classification_levels(layout, attr_map)
        for i in range(5):
            result[f"classification_level_{i + 1}_name"] = levels[i]
        results.append(result)

    return results


def _compute_classification_levels(
    layout: ClassificationLayout | None,
    attr_map: dict[str, dict[str, str | None]],
) -> list[str | None]:
    """레이아웃 기반 분류 레벨 라벨 계산. DB 쿼리 없음."""
    levels: list[str | None] = [None, None, None, None, None]
    if not attr_map:
        return levels
    if layout is None:
        ordered = [attr_map.get("domain"), attr_map.get("imp_type"), attr_map.get("product_family"), attr_map.get("platform")]
        for idx, item in enumerate([entry["label"] for entry in ordered if entry], start=0):
            if idx >= len(levels):
                break
            levels[idx] = item
        return levels
    for idx, level in enumerate(sorted(layout.levels, key=lambda item: (item.level_no, item.id))[:5]):
        labels: list[str] = []
        joiner = level.joiner or ", "
        for key in sorted(level.keys, key=lambda item: (item.sort_order, item.id)):
            if not key.is_visible or key.attribute is None:
                continue
            entry = attr_map.get(key.attribute.attribute_key)
            if entry and entry["label"]:
                labels.append(entry["label"])
        levels[idx] = joiner.join(labels) if labels else None
    return levels


def _get_product_classification_meta(db: Session, product: ProductCatalog) -> dict[str, list[str | None]]:
    levels: list[str | None] = [None, None, None, None, None]
    attrs = _get_product_attribute_map(db, product.id)
    if not attrs:
        return {"levels": levels}
    layout = db.scalar(
        select(ClassificationLayout)
        .options(
            selectinload(ClassificationLayout.levels)
            .selectinload(ClassificationLayoutLevel.keys)
            .selectinload(ClassificationLayoutLevelKey.attribute)
        )
        .where(
            ClassificationLayout.scope_type == "global",
            ClassificationLayout.is_active.is_(True),
            ClassificationLayout.is_default.is_(True),
        )
        .order_by(ClassificationLayout.id.asc())
    )
    if layout is None:
        ordered = [attrs.get("domain"), attrs.get("imp_type"), attrs.get("product_family"), attrs.get("platform")]
        for idx, item in enumerate([entry["label"] for entry in ordered if entry], start=0):
            if idx >= len(levels):
                break
            levels[idx] = item
        return {"levels": levels}
    for idx, level in enumerate(sorted(layout.levels, key=lambda item: (item.level_no, item.id))[:5]):
        labels: list[str] = []
        joiner = level.joiner or ", "
        for key in sorted(level.keys, key=lambda item: (item.sort_order, item.id)):
            if not key.is_visible or key.attribute is None:
                continue
            entry = attrs.get(key.attribute.attribute_key)
            if entry and entry["label"]:
                labels.append(entry["label"])
        levels[idx] = joiner.join(labels) if labels else None
    return {"levels": levels}


def _resolve_product_attribute_payload(
    payload: ProductCatalogCreate | ProductCatalogUpdate,
    *,
    product: ProductCatalog | None = None,
) -> ProductCatalogAttributesUpdate | None:
    if payload.attributes is not None:
        return ProductCatalogAttributesUpdate(attributes=payload.attributes)
    if product is not None and not any(
        getattr(payload, field, None) is not None
        for field in ("vendor", "name", "product_type")
    ):
        return None
    inferred = _infer_attributes_from_legacy_fields(
        vendor=getattr(payload, "vendor", None) if getattr(payload, "vendor", None) is not None else (product.vendor if product else None),
        name=getattr(payload, "name", None) if getattr(payload, "name", None) is not None else (product.name if product else None),
        product_type=getattr(payload, "product_type", None) if getattr(payload, "product_type", None) is not None else (product.product_type if product else None),
    )
    if not inferred:
        return None
    return ProductCatalogAttributesUpdate(attributes=inferred)


def _infer_attributes_from_legacy_fields(
    *,
    vendor: str | None,
    name: str | None,
    product_type: str | None,
) -> list[dict]:
    text = " ".join(
        [
            (vendor or ""),
            (name or ""),
            (product_type or ""),
        ]
    ).lower()
    imp_type = "svc" if (product_type or "") in {"service", "model"} else ("sw" if (product_type or "") == "software" else "hw")
    if "hw-sec" in text or any(token in text for token in ("fw", "firewall", "utm", "ips", "waf", "ddos", "vpn")):
        domain = "sec"
    elif "hw-net" in text or any(token in text for token in ("switch", "router", "l2", "l3", "l4", "network")):
        domain = "net"
    elif "hw-str" in text or any(token in text for token in ("storage", "nas", "san", "backup")):
        domain = "sto"
    elif "sw-db" in text or any(token in text for token in ("oracle", "mssql", "mysql", "postgres", "dbms")):
        domain = "db"
    else:
        domain = "svr"
    family = "generic"
    if any(token in text for token in ("fw", "firewall", "utm", "srx", "fortigate", "ngf", "pan os")):
        family = "fw"
    elif "ips" in text:
        family = "ips"
    elif "waf" in text:
        family = "waf"
    elif "ddos" in text:
        family = "ddos"
    elif any(token in text for token in (" l2 ", "-l2", " l2-", "switch l2")):
        family = "l2"
    elif any(token in text for token in (" l3 ", "-l3", " l3-", "switch l3", "router")):
        family = "l3"
    elif any(token in text for token in (" l4 ", "-l4", " l4-", "adc", "load balancer", "loadbalancer")):
        family = "l4"
    elif any(token in text for token in ("poweredge", "proliant", "x86 server", "x86")):
        family = "x86_server"
    elif "unix" in text:
        family = "unix_server"
    elif "nas" in text:
        family = "nas"
    elif "san" in text:
        family = "san"
    elif any(token in text for token in ("oracle", "mssql", "mysql", "postgres", "dbms")):
        family = "dbms"
    elif any(token in text for token in ("windows", "linux", "운영체제", "os")):
        family = "os"
    elif "middleware" in text:
        family = "middleware"
    attrs = [
        {"attribute_key": "domain", "option_key": domain, "raw_value": None},
        {"attribute_key": "imp_type", "option_key": imp_type, "raw_value": None},
        {"attribute_key": "product_family", "option_key": family, "raw_value": None},
    ]
    if family in {"fw", "ips", "waf", "ddos", "nas", "san"} and any(token in text for token in ("srx", "fortigate", "ngf", "appliance")):
        attrs.append({"attribute_key": "platform", "option_key": "appliance", "raw_value": None})
    elif any(token in text for token in ("poweredge", "proliant", "x86")):
        attrs.append({"attribute_key": "platform", "option_key": "x86", "raw_value": None})
    elif "windows" in text:
        attrs.append({"attribute_key": "platform", "option_key": "windows", "raw_value": None})
    elif "linux" in text:
        attrs.append({"attribute_key": "platform", "option_key": "linux", "raw_value": None})
    return attrs


def _get_product_attribute_map(db: Session, product_id: int) -> dict[str, dict[str, str | None]]:
    values = get_product_attributes(db, product_id)
    return {
        value["attribute_key"]: {
            "option_key": value.get("option_key"),
            "label": value.get("option_label") or value.get("option_key") or value.get("raw_value"),
        }
        for value in values
        if value.get("attribute_key")
    }


def _build_bulk_upsert_payload(row: ProductCatalogBulkUpsertRow) -> dict:
    attributes = []
    for attribute_key, option_key in (
        ("domain", row.domain),
        ("imp_type", row.imp_type),
        ("product_family", row.product_family),
        ("platform", row.platform),
    ):
        cleaned = (option_key or "").strip()
        if not cleaned:
            continue
        attributes.append(
            {
                "attribute_key": attribute_key,
                "option_key": cleaned,
            }
        )
    payload = {
        "vendor": row.vendor.strip(),
        "name": row.name.strip(),
        "product_type": (row.product_type or "hardware").strip(),
        "version": (row.version or None),
        "reference_url": (row.reference_url or None),
        "eos_date": row.eos_date,
        "eosl_date": row.eosl_date,
        "eosl_note": (row.eosl_note or None),
    }
    if attributes:
        payload["attributes"] = attributes
    return payload

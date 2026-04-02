from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

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
from app.modules.infra.models.classification_node import ClassificationNode
from app.modules.infra.models.classification_scheme import ClassificationScheme
from app.modules.infra.models.hardware_spec import HardwareSpec
from app.modules.infra.models.software_spec import SoftwareSpec
from app.modules.infra.models.model_spec import ModelSpec
from app.modules.infra.models.generic_catalog_profile import GenericCatalogProfile
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.schemas.product_catalog import (
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


# ── ProductCatalog CRUD ──


def list_products(
    db: Session,
    vendor: str | None = None,
    product_type: str | None = None,
    category: str | None = None,
    q: str | None = None,
) -> list[dict]:
    stmt = select(ProductCatalog).order_by(
        ProductCatalog.vendor.asc(), ProductCatalog.name.asc()
    )
    if vendor is not None:
        stmt = stmt.where(ProductCatalog.vendor == vendor)
    if product_type is not None:
        stmt = stmt.where(ProductCatalog.product_type == product_type)
    if category is not None:
        stmt = stmt.where(ProductCatalog.category == category)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(ProductCatalog.name.ilike(like), ProductCatalog.vendor.ilike(like))
        )
    rows = list(db.scalars(stmt))
    return [_serialize_product(db, row) for row in rows]


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
    _ensure_vendor_name_unique(db, payload.vendor, payload.name)
    normalized = _normalize_catalog_classification(
        db,
        classification_node_code=payload.classification_node_code,
        category=payload.category,
        product_type=payload.product_type,
    )
    product = ProductCatalog(
        **payload.model_dump(exclude={"classification_node_code", "category", "product_type"}),
        classification_node_code=normalized["classification_node_code"],
        category=normalized["category"],
        product_type=normalized["product_type"],
    )
    db.add(product)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="product_catalog",
        entity_id=None, summary=f"제품 등록: {product.vendor} {product.name}",
        module="infra",
    )
    db.commit()
    db.refresh(product)
    return _serialize_product(db, product)


def update_product(
    db: Session, product_id: int, payload: ProductCatalogUpdate, current_user: User
) -> ProductCatalog:
    _require_edit(current_user)
    product = get_product(db, product_id)
    changes = payload.model_dump(exclude_unset=True)

    new_vendor = changes.get("vendor", product.vendor)
    new_name = changes.get("name", product.name)
    if new_vendor != product.vendor or new_name != product.name:
        _ensure_vendor_name_unique(db, new_vendor, new_name, product_id)
    if "classification_node_code" in changes or "category" in changes or "product_type" in changes:
        normalized = _normalize_catalog_classification(
            db,
            classification_node_code=changes.get(
                "classification_node_code", product.classification_node_code
            ),
            category=changes.get("category", product.category),
            product_type=changes.get("product_type", product.product_type),
        )
        changes["classification_node_code"] = normalized["classification_node_code"]
        changes["category"] = normalized["category"]
        changes["product_type"] = normalized["product_type"]

    for field, value in changes.items():
        setattr(product, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="product_catalog",
        entity_id=product.id, summary=f"제품 수정: {product.vendor} {product.name}",
        module="infra",
    )
    db.commit()
    db.refresh(product)
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


def _normalize_catalog_classification(
    db: Session,
    *,
    classification_node_code: str | None,
    category: str | None,
    product_type: str | None,
) -> dict[str, str | None]:
    code = (classification_node_code or "").strip() or None
    if code:
        node = _get_global_catalog_classification_node(db, code)
        return {
            "classification_node_code": node.node_code,
            "category": node.node_name,
            "product_type": node.asset_kind or product_type or "hardware",
        }
    if category and category.strip():
        return {
            "classification_node_code": None,
            "category": category.strip(),
            "product_type": product_type or "hardware",
        }
    raise BusinessRuleError(
        "카탈로그 최종 분류를 선택하세요.", status_code=422
    )


def _get_global_catalog_classification_node(db: Session, node_code: str) -> ClassificationNode:
    scheme = db.scalar(
        select(ClassificationScheme)
        .where(ClassificationScheme.scope_type == "global")
        .order_by(ClassificationScheme.id.asc())
    )
    if scheme is None:
        raise BusinessRuleError("글로벌 기본 분류체계가 없습니다.", status_code=409)
    nodes = list(
        db.scalars(
            select(ClassificationNode).where(ClassificationNode.scheme_id == scheme.id)
        )
    )
    node_map = {node.node_code: node for node in nodes}
    node = node_map.get(node_code)
    if node is None:
        raise NotFoundError("글로벌 기본 분류체계에 해당 분류코드가 없습니다.")
    if not node.is_active:
        raise BusinessRuleError("비활성 분류 항목은 카탈로그에 연결할 수 없습니다.", status_code=422)
    if not node.is_catalog_assignable:
        raise BusinessRuleError("카탈로그에 연결 가능한 분류만 선택할 수 있습니다.", status_code=422)
    if not node.asset_type_key or not node.asset_type_code or not node.asset_type_label or not node.asset_kind:
        raise BusinessRuleError("선택한 분류에 자산유형 메타가 완성되어 있지 않습니다.", status_code=422)
    return node


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
    type_meta = _get_product_asset_type_meta(db, product)
    classification_meta = _get_product_classification_meta(db, product)
    result["asset_type_key"] = type_meta["asset_type_key"]
    result["asset_type_code"] = type_meta["asset_type_code"]
    result["asset_type_label"] = type_meta["asset_type_label"]
    result["classification_level_1_name"] = classification_meta["levels"][0]
    result["classification_level_2_name"] = classification_meta["levels"][1]
    result["classification_level_3_name"] = classification_meta["levels"][2]
    result["classification_level_4_name"] = classification_meta["levels"][3]
    result["classification_level_5_name"] = classification_meta["levels"][4]
    return result


def _get_product_asset_type_meta(db: Session, product: ProductCatalog) -> dict[str, str | None]:
    if not product.classification_node_code:
        return {"asset_type_key": None, "asset_type_code": None, "asset_type_label": None}
    node = db.scalar(
        select(ClassificationNode)
        .join(ClassificationScheme, ClassificationScheme.id == ClassificationNode.scheme_id)
        .where(
            ClassificationScheme.scope_type == "global",
            ClassificationNode.node_code == product.classification_node_code,
        )
        .order_by(ClassificationScheme.id.asc())
    )
    if node is None:
        return {"asset_type_key": None, "asset_type_code": None, "asset_type_label": None}
    return {
        "asset_type_key": node.asset_type_key,
        "asset_type_code": node.asset_type_code,
        "asset_type_label": node.asset_type_label,
    }


def _get_product_classification_meta(db: Session, product: ProductCatalog) -> dict[str, list[str | None]]:
    levels: list[str | None] = [None, None, None, None, None]
    if not product.classification_node_code:
        return {"levels": levels}
    node = db.scalar(
        select(ClassificationNode)
        .join(ClassificationScheme, ClassificationScheme.id == ClassificationNode.scheme_id)
        .where(
            ClassificationScheme.scope_type == "global",
            ClassificationNode.node_code == product.classification_node_code,
        )
        .order_by(ClassificationScheme.id.asc())
    )
    if node is None:
        return {"levels": levels}
    nodes = list(
        db.scalars(
            select(ClassificationNode).where(ClassificationNode.scheme_id == node.scheme_id)
        )
    )
    node_map = {item.id: item for item in nodes}
    parts = [node.node_name]
    parent_id = node.parent_id
    while parent_id:
        parent = node_map.get(parent_id)
        if parent is None:
            break
        parts.append(parent.node_name)
        parent_id = parent.parent_id
    parts.reverse()
    for idx, part in enumerate(parts[:5]):
        levels[idx] = part
    return {"levels": levels}

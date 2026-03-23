from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.modules.common.models.user import User
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.hardware_spec import HardwareSpec
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.schemas.product_catalog import (
    ProductCatalogCreate,
    ProductCatalogUpdate,
)
from app.modules.infra.schemas.hardware_spec import HardwareSpecCreate, HardwareSpecUpdate
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
) -> list[ProductCatalog]:
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
        stmt = stmt.where(ProductCatalog.name.ilike(like))
    return list(db.scalars(stmt))


def get_product(db: Session, product_id: int) -> ProductCatalog:
    product = db.get(ProductCatalog, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    return product


def get_product_detail(db: Session, product_id: int) -> dict:
    """제품 상세 조회 (spec + interfaces 포함)."""
    product = get_product(db, product_id)
    spec = db.scalar(
        select(HardwareSpec).where(HardwareSpec.product_id == product_id)
    )
    interfaces = list(
        db.scalars(
            select(HardwareInterface)
            .where(HardwareInterface.product_id == product_id)
            .order_by(HardwareInterface.id.asc())
        )
    )
    result = {c.key: getattr(product, c.key) for c in product.__table__.columns}
    result["hardware_spec"] = spec
    result["interfaces"] = interfaces
    return result


def create_product(
    db: Session, payload: ProductCatalogCreate, current_user: User
) -> ProductCatalog:
    _require_edit(current_user)
    _ensure_vendor_name_unique(db, payload.vendor, payload.name)

    product = ProductCatalog(**payload.model_dump())
    db.add(product)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="product_catalog",
        entity_id=None, summary=f"제품 등록: {product.vendor} {product.name}",
        module="infra",
    )
    db.commit()
    db.refresh(product)
    return product


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

    for field, value in changes.items():
        setattr(product, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="product_catalog",
        entity_id=product.id, summary=f"제품 수정: {product.vendor} {product.name}",
        module="infra",
    )
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int, current_user: User) -> None:
    _require_edit(current_user)
    product = get_product(db, product_id)

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
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


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

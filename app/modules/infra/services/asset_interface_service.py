from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
)
from app.modules.common.models.user import User
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_interface import AssetInterface
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.schemas.asset_interface import (
    AssetInterfaceCreate,
    AssetInterfaceUpdate,
)

VALID_IF_TYPES = frozenset(
    {"physical", "lag", "vlan", "subinterface", "loopback", "tunnel", "virtual"}
)


# ── Public API ──


def list_interfaces(db: Session, asset_id: int) -> list[AssetInterface]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetInterface)
            .where(AssetInterface.asset_id == asset_id)
            .order_by(AssetInterface.sort_order.asc(), AssetInterface.name.asc())
        )
    )


def get_interface(db: Session, interface_id: int) -> AssetInterface:
    iface = db.get(AssetInterface, interface_id)
    if iface is None:
        raise NotFoundError("Asset interface not found")
    return iface


def create_interface(
    db: Session, payload: AssetInterfaceCreate, current_user: User
) -> AssetInterface:
    _require_inventory_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)
    _validate_if_type(payload.if_type)
    _ensure_name_unique(db, payload.asset_id, payload.name)

    if payload.parent_id is not None:
        _validate_parent(db, payload.parent_id, payload.asset_id)

    iface = AssetInterface(**payload.model_dump())
    db.add(iface)
    db.commit()
    db.refresh(iface)
    return iface


def update_interface(
    db: Session, interface_id: int, payload: AssetInterfaceUpdate, current_user: User
) -> AssetInterface:
    _require_inventory_edit(current_user)
    iface = get_interface(db, interface_id)
    changes = payload.model_dump(exclude_unset=True)

    if "if_type" in changes and changes["if_type"] is not None:
        _validate_if_type(changes["if_type"])

    if "name" in changes and changes["name"] is not None and changes["name"] != iface.name:
        _ensure_name_unique(db, iface.asset_id, changes["name"], exclude_id=interface_id)

    for field, value in changes.items():
        setattr(iface, field, value)

    db.commit()
    db.refresh(iface)
    return iface


def delete_interface(db: Session, interface_id: int, current_user: User) -> None:
    _require_inventory_edit(current_user)
    iface = get_interface(db, interface_id)
    db.delete(iface)
    db.commit()


def update_lag_members(
    db: Session, lag_id: int, member_ids: list[int], current_user: User
) -> None:
    _require_inventory_edit(current_user)
    lag = get_interface(db, lag_id)

    if lag.if_type != "lag":
        raise BusinessRuleError("Target interface must be LAG type")

    # Clear existing members
    old_members = list(
        db.scalars(
            select(AssetInterface).where(AssetInterface.parent_id == lag_id)
        )
    )
    for m in old_members:
        m.parent_id = None

    # Assign new members
    for mid in member_ids:
        member = get_interface(db, mid)
        if member.asset_id != lag.asset_id:
            raise BusinessRuleError("LAG member must belong to the same asset")
        if member.if_type != "physical":
            raise BusinessRuleError("LAG member must be physical type")
        member.parent_id = lag_id

    db.commit()


def generate_interfaces_from_catalog(
    db: Session, asset_id: int, current_user: User
) -> list[AssetInterface]:
    _require_inventory_edit(current_user)
    created = sync_interfaces_from_catalog_model(db, asset_id, replace_catalog_generated=False)
    db.commit()
    for iface in created:
        db.refresh(iface)
    return created


def sync_interfaces_from_catalog_model(
    db: Session,
    asset_id: int,
    *,
    replace_catalog_generated: bool = True,
) -> list[AssetInterface]:
    """Create asset interfaces from the assigned hardware catalog model.

    When replacing, only previously catalog-generated rows (hw_interface_id set) are
    deleted. Manual interfaces/LAGs/VLANs are preserved.
    """
    asset = _ensure_asset_exists(db, asset_id)

    if not asset.model_id:
        raise BusinessRuleError("Asset has no catalog model assigned")

    hw_specs = list(
        db.scalars(
            select(HardwareInterface)
            .where(HardwareInterface.product_id == asset.model_id)
            .order_by(HardwareInterface.id.asc())
        )
    )

    if replace_catalog_generated:
        old_generated = list(
            db.scalars(
                select(AssetInterface).where(
                    AssetInterface.asset_id == asset_id,
                    AssetInterface.hw_interface_id.is_not(None),
                )
            )
        )
        for iface in old_generated:
            db.delete(iface)
        if old_generated:
            db.flush()

    created: list[AssetInterface] = []
    name_group_indexes: dict[str, int] = {}
    existing_names = set(
        db.scalars(select(AssetInterface.name).where(AssetInterface.asset_id == asset_id))
    )
    sort_base = db.scalar(
        select(AssetInterface.sort_order)
        .where(AssetInterface.asset_id == asset_id)
        .order_by(AssetInterface.sort_order.desc())
        .limit(1)
    )
    next_sort = (sort_base or 0) + 1

    for spec in hw_specs:
        name_prefix = _catalog_name_prefix(spec)
        if name_prefix is None:
            continue
        port_type = _catalog_port_type(spec)
        is_modular = spec.capacity_type == "modular"
        if name_prefix == "MGMT":
            group_index = 0
        else:
            group_index = name_group_indexes.setdefault(name_prefix, len(name_group_indexes))

        for i in range(spec.count or 0):
            if is_modular:
                slot_label = spec.note or f"slot{spec.id}"
                name = f"{slot_label}/port{i + 1}"
                oper_status = "not_present"
            else:
                name = _port_name(name_prefix, group_index, i + 1)
                oper_status = None

            # Idempotent/preserve manual: skip conflicting names.
            if name in existing_names:
                continue
            existing_names.add(name)

            iface = AssetInterface(
                asset_id=asset_id,
                hw_interface_id=spec.id,
                name=name,
                if_type="physical",
                port_type=port_type,
                speed=spec.speed,
                media_type=spec.connector_type,
                admin_status="up",
                oper_status=oper_status,
                sort_order=next_sort,
            )
            next_sort += 1
            db.add(iface)
            created.append(iface)

    return created



def _catalog_name_prefix(spec: HardwareInterface) -> str | None:
    text = " ".join(filter(None, [spec.interface_type, spec.speed, spec.connector_type, spec.note])).lower()
    if "console" in text:
        return None
    if "mgmt" in text or "management" in text:
        return "MGMT"
    if "infini" in text:
        return "IB"
    if "200g" in text:
        return "200GE"
    if "100g" in text:
        return "100GE"
    if "50g" in text:
        return "50GE"
    if "25g" in text:
        return "25GE"
    if "10g" in text or "sfp+" in text or "10ge" in text:
        return "TE"
    if "40g" in text or "qsfp+" in text:
        return "40GE"
    if "1g" in text or "ge" in text or "ethernet" in text or "rj45" in text or "sfp" in text:
        return "GE"
    return (spec.interface_type or "IF").upper().replace(" ", "-")[:30]


def _catalog_port_type(spec: HardwareInterface) -> str | None:
    connector = (spec.connector_type or "").strip()
    if connector:
        normalized = connector.replace("RJ-45", "RJ45").replace("RJ 45", "RJ45")
        return normalized[:30]
    interface_type = (spec.interface_type or "").strip()
    if interface_type:
        for token in ["SFP56", "SFP28", "SFP+", "SFP", "QSFP28", "QSFP+", "QSFP", "RJ45"]:
            if token.lower() in interface_type.lower():
                return token
        return interface_type[:30]
    return None


def _port_name(name_prefix: str, group_index: int, number: int) -> str:
    if name_prefix == "MGMT":
        return f"MGMT-0/{number}"
    if name_prefix == "IB":
        return f"IB-{group_index}/0/{number}"
    return f"{name_prefix}-{group_index}/0/{number}"

# ── Private helpers ──


def _require_inventory_edit(current_user) -> None:
    from app.modules.infra.services.network_service import (
        _require_inventory_edit as _req,
    )

    _req(current_user)


def _ensure_asset_exists(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def _validate_if_type(if_type: str) -> None:
    if if_type not in VALID_IF_TYPES:
        raise BusinessRuleError(
            f"Invalid interface type: {if_type}. Must be one of {sorted(VALID_IF_TYPES)}"
        )


def _ensure_name_unique(
    db: Session, asset_id: int, name: str, *, exclude_id: int | None = None
) -> None:
    stmt = select(AssetInterface.id).where(
        AssetInterface.asset_id == asset_id,
        AssetInterface.name == name,
    )
    existing = db.scalar(stmt)
    if existing is not None and existing != exclude_id:
        raise DuplicateError(f"Interface name '{name}' already exists on this asset")


def _validate_parent(db: Session, parent_id: int, asset_id: int) -> None:
    parent = db.get(AssetInterface, parent_id)
    if parent is None:
        raise NotFoundError("Parent interface not found")
    if parent.asset_id != asset_id:
        raise BusinessRuleError("Parent interface must belong to the same asset")
    if parent.if_type != "lag":
        raise BusinessRuleError("Parent interface must be LAG type")

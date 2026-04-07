from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_interface import AssetInterface
from app.modules.infra.models.asset_ip import AssetIP
from app.modules.infra.models.ip_subnet import IpSubnet
from app.modules.infra.models.port_map import PortMap
from app.modules.infra.schemas.asset_ip import AssetIPCreate, AssetIPUpdate
from app.modules.infra.schemas.ip_subnet import IpSubnetCreate, IpSubnetUpdate
from app.modules.infra.schemas.port_map import PortMapCreate, PortMapUpdate
from app.modules.infra.services._helpers import (
    ensure_partner_exists,
    get_period_asset_ids,
)


# ── IpSubnet ──


def list_subnets(db: Session, partner_id: int) -> list[IpSubnet]:
    ensure_partner_exists(db, partner_id)
    return list(
        db.scalars(
            select(IpSubnet)
            .where(IpSubnet.partner_id == partner_id)
            .order_by(IpSubnet.name.asc())
        )
    )


def get_subnet(db: Session, subnet_id: int) -> IpSubnet:
    subnet = db.get(IpSubnet, subnet_id)
    if subnet is None:
        raise NotFoundError("IP subnet not found")
    return subnet


def create_subnet(db: Session, payload: IpSubnetCreate, current_user) -> IpSubnet:
    _require_inventory_edit(current_user)
    ensure_partner_exists(db, payload.partner_id)

    subnet = IpSubnet(**payload.model_dump())
    db.add(subnet)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="ip_subnet",
        entity_id=None, summary=f"IP대역 생성: {subnet.name}", module="infra",
    )
    db.commit()
    db.refresh(subnet)
    return subnet


def update_subnet(
    db: Session, subnet_id: int, payload: IpSubnetUpdate, current_user
) -> IpSubnet:
    _require_inventory_edit(current_user)
    subnet = get_subnet(db, subnet_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(subnet, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="ip_subnet",
        entity_id=subnet.id, summary=f"IP대역 수정: {subnet.name}", module="infra",
    )
    db.commit()
    db.refresh(subnet)
    return subnet


def delete_subnet(db: Session, subnet_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    subnet = get_subnet(db, subnet_id)

    has_ips = db.scalar(
        select(AssetIP.id).where(AssetIP.ip_subnet_id == subnet_id).limit(1)
    )
    if has_ips is not None:
        raise BusinessRuleError("Subnet with assigned IPs cannot be deleted")

    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="ip_subnet",
        entity_id=subnet.id, summary=f"IP대역 삭제: {subnet.name}", module="infra",
    )
    db.delete(subnet)
    db.commit()


# ── AssetIP ──


def list_asset_ips(db: Session, asset_id: int) -> list[AssetIP]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetIP)
            .join(AssetInterface, AssetIP.interface_id == AssetInterface.id)
            .where(AssetInterface.asset_id == asset_id)
            .order_by(AssetIP.ip_address.asc())
        )
    )


def list_partner_ips(db: Session, partner_id: int) -> list[AssetIP]:
    """업체 전체 IP 인벤토리 조회."""
    ensure_partner_exists(db, partner_id)
    return list(
        db.scalars(
            select(AssetIP)
            .join(AssetInterface, AssetIP.interface_id == AssetInterface.id)
            .join(Asset, AssetInterface.asset_id == Asset.id)
            .where(Asset.partner_id == partner_id)
            .order_by(AssetIP.ip_address.asc())
        )
    )


def get_asset_ip(db: Session, ip_id: int) -> AssetIP:
    asset_ip = db.get(AssetIP, ip_id)
    if asset_ip is None:
        raise NotFoundError("Asset IP not found")
    return asset_ip


def create_asset_ip(db: Session, payload: AssetIPCreate, current_user) -> AssetIP:
    _require_inventory_edit(current_user)
    iface = db.get(AssetInterface, payload.interface_id)
    if iface is None:
        raise NotFoundError("Interface not found")
    asset = db.get(Asset, iface.asset_id)

    if payload.ip_subnet_id is not None:
        _ensure_subnet_exists(db, payload.ip_subnet_id)

    _ensure_ip_unique_in_partner(db, asset.partner_id, payload.ip_address)

    asset_ip = AssetIP(**payload.model_dump())
    db.add(asset_ip)
    db.commit()
    db.refresh(asset_ip)
    return asset_ip


def update_asset_ip(
    db: Session, ip_id: int, payload: AssetIPUpdate, current_user
) -> AssetIP:
    _require_inventory_edit(current_user)
    asset_ip = get_asset_ip(db, ip_id)
    changes = payload.model_dump(exclude_unset=True)

    if "ip_subnet_id" in changes and changes["ip_subnet_id"] is not None:
        _ensure_subnet_exists(db, changes["ip_subnet_id"])

    if "ip_address" in changes and changes["ip_address"] != asset_ip.ip_address:
        iface = db.get(AssetInterface, asset_ip.interface_id)
        asset = db.get(Asset, iface.asset_id)
        _ensure_ip_unique_in_partner(db, asset.partner_id, changes["ip_address"], ip_id)

    for field, value in changes.items():
        setattr(asset_ip, field, value)

    db.commit()
    db.refresh(asset_ip)
    return asset_ip


def delete_asset_ip(db: Session, ip_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    asset_ip = get_asset_ip(db, ip_id)
    db.delete(asset_ip)
    db.commit()


# ── AssetIP helpers ──


def build_ip_interface_map(
    db: Session, asset_ips: list[AssetIP]
) -> dict[int, dict]:
    """Collect interface_ids from asset_ips and return enrichment dict keyed by interface_id."""
    iface_ids: set[int] = {ip.interface_id for ip in asset_ips if ip.interface_id}
    if not iface_ids:
        return {}

    rows = db.execute(
        select(
            AssetInterface.id,
            AssetInterface.name,
            AssetInterface.if_type,
            Asset.asset_name,
        )
        .join(Asset, AssetInterface.asset_id == Asset.id)
        .where(AssetInterface.id.in_(iface_ids))
    ).all()

    return {
        row.id: {
            "interface_name": row.name,
            "if_type": row.if_type,
            "asset_name": row.asset_name,
        }
        for row in rows
    }


def enrich_asset_ip(ip: AssetIP, iface_map: dict[int, dict]) -> dict:
    """Convert AssetIP ORM to dict enriched with interface/asset fields."""
    data = {col.name: getattr(ip, col.name) for col in ip.__table__.columns}
    info = iface_map.get(ip.interface_id)
    data["asset_name"] = info["asset_name"] if info else None
    data["interface_name"] = info["interface_name"] if info else None
    data["if_type"] = info["if_type"] if info else None
    return data


# ── PortMap helpers ──


def build_interface_map(
    db: Session, port_maps: list[PortMap]
) -> dict[int, dict]:
    """Collect src/dst interface IDs from port_maps and return enrichment dict."""
    iface_ids: set[int] = set()
    for pm in port_maps:
        if pm.src_interface_id is not None:
            iface_ids.add(pm.src_interface_id)
        if pm.dst_interface_id is not None:
            iface_ids.add(pm.dst_interface_id)

    if not iface_ids:
        return {}

    rows = db.execute(
        select(
            AssetInterface.id,
            AssetInterface.name,
            Asset.id.label("asset_id"),
            Asset.asset_name,
            Asset.hostname,
            Asset.zone,
        )
        .join(Asset, AssetInterface.asset_id == Asset.id)
        .where(AssetInterface.id.in_(iface_ids))
    ).all()

    return {
        row.id: {
            "asset_id": row.asset_id,
            "asset_name": row.asset_name,
            "hostname": row.hostname,
            "iface_name": row.name,
            "zone": row.zone,
        }
        for row in rows
    }


def enrich_port_map(pm: PortMap, iface_map: dict[int, dict]) -> dict:
    """Convert PortMap ORM to dict enriched with denormalized interface/asset fields."""
    data = {col.name: getattr(pm, col.name) for col in pm.__table__.columns}

    src_info = iface_map.get(pm.src_interface_id) if pm.src_interface_id is not None else None
    data["src_asset_id"] = src_info["asset_id"] if src_info else None
    data["src_asset_name"] = src_info["asset_name"] if src_info else None
    data["src_hostname"] = src_info["hostname"] if src_info else None
    data["src_interface_name"] = src_info["iface_name"] if src_info else None
    data["src_zone"] = src_info["zone"] if src_info else None

    dst_info = iface_map.get(pm.dst_interface_id) if pm.dst_interface_id is not None else None
    data["dst_asset_id"] = dst_info["asset_id"] if dst_info else None
    data["dst_asset_name"] = dst_info["asset_name"] if dst_info else None
    data["dst_hostname"] = dst_info["hostname"] if dst_info else None
    data["dst_interface_name"] = dst_info["iface_name"] if dst_info else None
    data["dst_zone"] = dst_info["zone"] if dst_info else None

    return data


# ── PortMap ──


def list_port_maps(
    db: Session, partner_id: int, period_id: int | None = None
) -> list[PortMap]:
    ensure_partner_exists(db, partner_id)
    stmt = select(PortMap).where(PortMap.partner_id == partner_id)
    if period_id is not None:
        asset_ids = get_period_asset_ids(db, period_id)
        # Filter by interfaces belonging to period assets
        iface_ids_stmt = (
            select(AssetInterface.id).where(AssetInterface.asset_id.in_(asset_ids))
        )
        stmt = stmt.where(
            or_(
                PortMap.src_interface_id.in_(iface_ids_stmt),
                PortMap.dst_interface_id.in_(iface_ids_stmt),
                and_(
                    PortMap.src_interface_id.is_(None),
                    PortMap.dst_interface_id.is_(None),
                ),
            )
        )
    return list(db.scalars(stmt.order_by(PortMap.id.asc())))


def get_port_map(db: Session, port_map_id: int) -> PortMap:
    port_map = db.get(PortMap, port_map_id)
    if port_map is None:
        raise NotFoundError("Port map not found")
    return port_map


def create_port_map(db: Session, payload: PortMapCreate, current_user) -> PortMap:
    _require_inventory_edit(current_user)
    ensure_partner_exists(db, payload.partner_id)

    if payload.src_interface_id is not None:
        iface = db.get(AssetInterface, payload.src_interface_id)
        if iface is None:
            raise NotFoundError("Source interface not found")
    if payload.dst_interface_id is not None:
        iface = db.get(AssetInterface, payload.dst_interface_id)
        if iface is None:
            raise NotFoundError("Destination interface not found")

    port_map = PortMap(**payload.model_dump())
    db.add(port_map)
    audit.log(
        db, user_id=current_user.id, action="create", entity_type="port_map",
        entity_id=None, summary=f"포트맵 생성: {port_map.summary or ''}", module="infra",
    )
    db.commit()
    db.refresh(port_map)
    return port_map


def update_port_map(
    db: Session, port_map_id: int, payload: PortMapUpdate, current_user
) -> PortMap:
    _require_inventory_edit(current_user)
    port_map = get_port_map(db, port_map_id)
    changes = payload.model_dump(exclude_unset=True)

    if "src_interface_id" in changes and changes["src_interface_id"] is not None:
        iface = db.get(AssetInterface, changes["src_interface_id"])
        if iface is None:
            raise NotFoundError("Source interface not found")
    if "dst_interface_id" in changes and changes["dst_interface_id"] is not None:
        iface = db.get(AssetInterface, changes["dst_interface_id"])
        if iface is None:
            raise NotFoundError("Destination interface not found")

    for field, value in changes.items():
        setattr(port_map, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="port_map",
        entity_id=port_map.id, summary=f"포트맵 수정: {port_map.summary or ''}", module="infra",
    )
    db.commit()
    db.refresh(port_map)
    return port_map


def delete_port_map(db: Session, port_map_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    port_map = get_port_map(db, port_map_id)
    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="port_map",
        entity_id=port_map.id, summary=f"포트맵 삭제: {port_map.summary or ''}", module="infra",
    )
    db.delete(port_map)
    db.commit()


# ── Private helpers ──


def _ensure_asset_exists(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def _ensure_subnet_exists(db: Session, subnet_id: int) -> None:
    if db.get(IpSubnet, subnet_id) is None:
        raise NotFoundError("IP subnet not found")


def _ensure_asset_belongs_to_partner(
    db: Session, asset_id: int, partner_id: int
) -> None:
    asset = _ensure_asset_exists(db, asset_id)
    if asset.partner_id != partner_id:
        raise BusinessRuleError("Asset does not belong to this partner")


def _ensure_ip_unique_in_partner(
    db: Session, partner_id: int, ip_address: str, ip_id: int | None = None
) -> None:
    """업체 범위 내 IP 중복 검증."""
    stmt = (
        select(AssetIP)
        .join(AssetInterface, AssetIP.interface_id == AssetInterface.id)
        .join(Asset, AssetInterface.asset_id == Asset.id)
        .where(Asset.partner_id == partner_id, AssetIP.ip_address == ip_address)
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if ip_id is not None and existing.id == ip_id:
        return
    raise DuplicateError("이 고객사에 동일한 IP가 이미 존재합니다.")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

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
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_ip import AssetIP
from app.modules.infra.models.ip_subnet import IpSubnet
from app.modules.infra.models.port_map import PortMap
from app.modules.infra.models.project import Project
from app.modules.infra.schemas.asset_ip import AssetIPCreate, AssetIPUpdate
from app.modules.infra.schemas.ip_subnet import IpSubnetCreate, IpSubnetUpdate
from app.modules.infra.schemas.port_map import PortMapCreate, PortMapUpdate


# ── IpSubnet ──


def list_subnets(db: Session, project_id: int) -> list[IpSubnet]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(IpSubnet)
            .where(IpSubnet.project_id == project_id)
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
    _ensure_project_exists(db, payload.project_id)

    subnet = IpSubnet(**payload.model_dump())
    db.add(subnet)
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

    db.delete(subnet)
    db.commit()


# ── AssetIP ──


def list_asset_ips(db: Session, asset_id: int) -> list[AssetIP]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetIP)
            .where(AssetIP.asset_id == asset_id)
            .order_by(AssetIP.ip_address.asc())
        )
    )


def list_project_ips(db: Session, project_id: int) -> list[AssetIP]:
    """프로젝트 전체 IP 인벤토리 조회."""
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(AssetIP)
            .join(Asset, AssetIP.asset_id == Asset.id)
            .where(Asset.project_id == project_id)
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
    asset = _ensure_asset_exists(db, payload.asset_id)

    if payload.ip_subnet_id is not None:
        _ensure_subnet_exists(db, payload.ip_subnet_id)

    _ensure_ip_unique_in_project(db, asset.project_id, payload.ip_address)

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
        asset = db.get(Asset, asset_ip.asset_id)
        _ensure_ip_unique_in_project(db, asset.project_id, changes["ip_address"], ip_id)

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


# ── PortMap ──


def list_port_maps(db: Session, project_id: int) -> list[PortMap]:
    _ensure_project_exists(db, project_id)
    return list(
        db.scalars(
            select(PortMap)
            .where(PortMap.project_id == project_id)
            .order_by(PortMap.id.asc())
        )
    )


def get_port_map(db: Session, port_map_id: int) -> PortMap:
    port_map = db.get(PortMap, port_map_id)
    if port_map is None:
        raise NotFoundError("Port map not found")
    return port_map


def create_port_map(db: Session, payload: PortMapCreate, current_user) -> PortMap:
    _require_inventory_edit(current_user)
    _ensure_project_exists(db, payload.project_id)

    if payload.src_asset_id is not None:
        _ensure_asset_belongs_to_project(db, payload.src_asset_id, payload.project_id)
    if payload.dst_asset_id is not None:
        _ensure_asset_belongs_to_project(db, payload.dst_asset_id, payload.project_id)

    port_map = PortMap(**payload.model_dump())
    db.add(port_map)
    db.commit()
    db.refresh(port_map)
    return port_map


def update_port_map(
    db: Session, port_map_id: int, payload: PortMapUpdate, current_user
) -> PortMap:
    _require_inventory_edit(current_user)
    port_map = get_port_map(db, port_map_id)
    changes = payload.model_dump(exclude_unset=True)

    if "src_asset_id" in changes and changes["src_asset_id"] is not None:
        _ensure_asset_belongs_to_project(
            db, changes["src_asset_id"], port_map.project_id
        )
    if "dst_asset_id" in changes and changes["dst_asset_id"] is not None:
        _ensure_asset_belongs_to_project(
            db, changes["dst_asset_id"], port_map.project_id
        )

    for field, value in changes.items():
        setattr(port_map, field, value)

    db.commit()
    db.refresh(port_map)
    return port_map


def delete_port_map(db: Session, port_map_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    port_map = get_port_map(db, port_map_id)
    db.delete(port_map)
    db.commit()


# ── Private helpers ──


def _ensure_project_exists(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("Project not found")


def _ensure_asset_exists(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def _ensure_subnet_exists(db: Session, subnet_id: int) -> None:
    if db.get(IpSubnet, subnet_id) is None:
        raise NotFoundError("IP subnet not found")


def _ensure_asset_belongs_to_project(
    db: Session, asset_id: int, project_id: int
) -> None:
    asset = _ensure_asset_exists(db, asset_id)
    if asset.project_id != project_id:
        raise BusinessRuleError("Asset does not belong to this project")


def _ensure_ip_unique_in_project(
    db: Session, project_id: int, ip_address: str, ip_id: int | None = None
) -> None:
    """프로젝트 범위 내 IP 중복 검증."""
    stmt = (
        select(AssetIP)
        .join(Asset, AssetIP.asset_id == Asset.id)
        .where(Asset.project_id == project_id, AssetIP.ip_address == ip_address)
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if ip_id is not None and existing.id == ip_id:
        return
    raise DuplicateError("IP address already exists in this project")


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetIPCreate(BaseModel):
    asset_id: int
    ip_subnet_id: int | None = None
    ip_address: str
    ip_type: str = "service"
    interface_name: str | None = None
    is_primary: bool = False
    zone: str | None = None
    service_name: str | None = None
    hostname: str | None = None
    vlan_id: str | None = None
    network: str | None = None
    netmask: str | None = None
    gateway: str | None = None
    dns_primary: str | None = None
    dns_secondary: str | None = None
    note: str | None = None


class AssetIPUpdate(BaseModel):
    ip_subnet_id: int | None = None
    ip_address: str | None = None
    ip_type: str | None = None
    interface_name: str | None = None
    is_primary: bool | None = None
    zone: str | None = None
    service_name: str | None = None
    hostname: str | None = None
    vlan_id: str | None = None
    network: str | None = None
    netmask: str | None = None
    gateway: str | None = None
    dns_primary: str | None = None
    dns_secondary: str | None = None
    note: str | None = None


class AssetIPRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    ip_subnet_id: int | None
    ip_address: str
    ip_type: str
    interface_name: str | None
    is_primary: bool
    zone: str | None
    service_name: str | None
    hostname: str | None
    vlan_id: str | None
    network: str | None
    netmask: str | None
    gateway: str | None
    dns_primary: str | None
    dns_secondary: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetIPCreate(BaseModel):
    interface_id: int = 0
    ip_subnet_id: int | None = None
    ip_address: str
    ip_type: str = "service"
    is_primary: bool = False
    zone: str | None = None
    service_name: str | None = None
    hostname: str | None = None
    vlan_id: str | None = None
    note: str | None = None


class AssetIPUpdate(BaseModel):
    interface_id: int | None = None
    ip_subnet_id: int | None = None
    ip_address: str | None = None
    ip_type: str | None = None
    is_primary: bool | None = None
    zone: str | None = None
    service_name: str | None = None
    hostname: str | None = None
    vlan_id: str | None = None
    note: str | None = None


class AssetIPRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interface_id: int
    ip_subnet_id: int | None
    ip_address: str
    ip_type: str
    is_primary: bool
    zone: str | None
    service_name: str | None
    hostname: str | None
    vlan_id: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime
    # Enriched fields (not in DB, populated by router)
    asset_name: str | None = None
    interface_name: str | None = None
    if_type: str | None = None

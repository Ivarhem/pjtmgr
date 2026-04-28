from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetInterfaceCreate(BaseModel):
    asset_id: int = 0
    parent_id: int | None = None
    hw_interface_id: int | None = None
    name: str
    if_type: str = "physical"
    port_type: str | None = None
    slot: str | None = None
    slot_position: int | None = None
    speed: str | None = None
    media_type: str | None = None
    mac_address: str | None = None
    admin_status: str = "up"
    oper_status: str | None = None
    description: str | None = None
    sort_order: int = 0


class AssetInterfaceUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = None
    if_type: str | None = None
    port_type: str | None = None
    slot: str | None = None
    slot_position: int | None = None
    speed: str | None = None
    media_type: str | None = None
    mac_address: str | None = None
    admin_status: str | None = None
    oper_status: str | None = None
    description: str | None = None
    sort_order: int | None = None


class AssetInterfaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    parent_id: int | None
    hw_interface_id: int | None
    name: str
    if_type: str
    port_type: str | None
    slot: str | None
    slot_position: int | None
    speed: str | None
    media_type: str | None
    mac_address: str | None
    admin_status: str
    oper_status: str | None
    description: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class AssetInterfaceBulkCreate(BaseModel):
    asset_id: int
    generate_from_catalog: bool = True

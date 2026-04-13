from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortMapCreate(BaseModel):
    partner_id: int
    src_interface_id: int | None = None
    dst_interface_id: int | None = None
    src_asset_name_raw: str | None = None
    src_interface_name_raw: str | None = None
    dst_asset_name_raw: str | None = None
    dst_interface_name_raw: str | None = None
    protocol: str | None = None
    port: int | None = None
    purpose: str | None = None
    status: str = "required"
    note: str | None = None
    seq: int | None = None
    connection_type: str | None = None
    summary: str | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    cable_type: str | None = None
    media_category: str | None = None
    src_connector_type: str | None = None
    dst_connector_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapUpdate(BaseModel):
    src_interface_id: int | None = None
    dst_interface_id: int | None = None
    src_asset_name_raw: str | None = None
    src_interface_name_raw: str | None = None
    dst_asset_name_raw: str | None = None
    dst_interface_name_raw: str | None = None
    protocol: str | None = None
    port: int | None = None
    purpose: str | None = None
    status: str | None = None
    note: str | None = None
    seq: int | None = None
    connection_type: str | None = None
    summary: str | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    cable_type: str | None = None
    media_category: str | None = None
    src_connector_type: str | None = None
    dst_connector_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_id: int
    src_interface_id: int | None
    dst_interface_id: int | None
    src_asset_name_raw: str | None
    src_interface_name_raw: str | None
    dst_asset_name_raw: str | None
    dst_interface_name_raw: str | None
    protocol: str | None
    port: int | None
    purpose: str | None
    status: str
    note: str | None
    seq: int | None
    connection_type: str | None
    summary: str | None
    cable_no: str | None
    cable_request: str | None
    cable_type: str | None
    media_category: str | None
    src_connector_type: str | None
    dst_connector_type: str | None
    cable_speed: str | None
    duplex: str | None
    cable_category: str | None
    created_at: datetime
    updated_at: datetime

    # Denormalized fields enriched at query time
    src_asset_id: int | None = None
    src_asset_name: str | None = None
    src_hostname: str | None = None
    src_interface_name: str | None = None
    src_zone: str | None = None
    dst_asset_id: int | None = None
    dst_asset_name: str | None = None
    dst_hostname: str | None = None
    dst_interface_name: str | None = None
    dst_zone: str | None = None


class PortMapBulkUpdateItem(BaseModel):
    id: int
    changes: dict


class PortMapBulkUpdateRequest(BaseModel):
    items: list[PortMapBulkUpdateItem]

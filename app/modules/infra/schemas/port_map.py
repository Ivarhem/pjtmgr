from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortMapCreate(BaseModel):
    project_id: int
    src_asset_id: int | None = None
    src_ip: str | None = None
    dst_asset_id: int | None = None
    dst_ip: str | None = None
    protocol: str | None = None
    port: int | None = None
    purpose: str | None = None
    status: str = "required"
    note: str | None = None

    # Common
    seq: int | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    connection_type: str | None = None
    summary: str | None = None

    # Start side
    src_mid: str | None = None
    src_rack_no: str | None = None
    src_rack_unit: str | None = None
    src_vendor: str | None = None
    src_model: str | None = None
    src_hostname: str | None = None
    src_cluster: str | None = None
    src_slot: str | None = None
    src_port_name: str | None = None
    src_service_name: str | None = None
    src_zone: str | None = None
    src_vlan: str | None = None

    # End side
    dst_mid: str | None = None
    dst_rack_no: str | None = None
    dst_rack_unit: str | None = None
    dst_vendor: str | None = None
    dst_model: str | None = None
    dst_hostname: str | None = None
    dst_cluster: str | None = None
    dst_slot: str | None = None
    dst_port_name: str | None = None
    dst_service_name: str | None = None
    dst_zone: str | None = None
    dst_vlan: str | None = None

    # Cable info
    cable_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapUpdate(BaseModel):
    src_asset_id: int | None = None
    src_ip: str | None = None
    dst_asset_id: int | None = None
    dst_ip: str | None = None
    protocol: str | None = None
    port: int | None = None
    purpose: str | None = None
    status: str | None = None
    note: str | None = None

    # Common
    seq: int | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    connection_type: str | None = None
    summary: str | None = None

    # Start side
    src_mid: str | None = None
    src_rack_no: str | None = None
    src_rack_unit: str | None = None
    src_vendor: str | None = None
    src_model: str | None = None
    src_hostname: str | None = None
    src_cluster: str | None = None
    src_slot: str | None = None
    src_port_name: str | None = None
    src_service_name: str | None = None
    src_zone: str | None = None
    src_vlan: str | None = None

    # End side
    dst_mid: str | None = None
    dst_rack_no: str | None = None
    dst_rack_unit: str | None = None
    dst_vendor: str | None = None
    dst_model: str | None = None
    dst_hostname: str | None = None
    dst_cluster: str | None = None
    dst_slot: str | None = None
    dst_port_name: str | None = None
    dst_service_name: str | None = None
    dst_zone: str | None = None
    dst_vlan: str | None = None

    # Cable info
    cable_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    src_asset_id: int | None
    src_ip: str | None
    dst_asset_id: int | None
    dst_ip: str | None
    protocol: str | None
    port: int | None
    purpose: str | None
    status: str
    note: str | None
    created_at: datetime
    updated_at: datetime

    # Common
    seq: int | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    connection_type: str | None = None
    summary: str | None = None

    # Start side
    src_mid: str | None = None
    src_rack_no: str | None = None
    src_rack_unit: str | None = None
    src_vendor: str | None = None
    src_model: str | None = None
    src_hostname: str | None = None
    src_cluster: str | None = None
    src_slot: str | None = None
    src_port_name: str | None = None
    src_service_name: str | None = None
    src_zone: str | None = None
    src_vlan: str | None = None

    # End side
    dst_mid: str | None = None
    dst_rack_no: str | None = None
    dst_rack_unit: str | None = None
    dst_vendor: str | None = None
    dst_model: str | None = None
    dst_hostname: str | None = None
    dst_cluster: str | None = None
    dst_slot: str | None = None
    dst_port_name: str | None = None
    dst_service_name: str | None = None
    dst_zone: str | None = None
    dst_vlan: str | None = None

    # Cable info
    cable_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None

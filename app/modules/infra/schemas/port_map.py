from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortMapCreate(BaseModel):
    partner_id: int
    src_interface_id: int | None = None
    dst_interface_id: int | None = None
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
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapUpdate(BaseModel):
    src_interface_id: int | None = None
    dst_interface_id: int | None = None
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
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_id: int
    src_interface_id: int | None
    dst_interface_id: int | None
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
    cable_speed: str | None
    duplex: str | None
    cable_category: str | None
    created_at: datetime
    updated_at: datetime

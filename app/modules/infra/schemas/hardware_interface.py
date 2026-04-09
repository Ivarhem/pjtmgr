from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HardwareInterfaceCreate(BaseModel):
    interface_type: str
    speed: str | None = None
    count: int
    connector_type: str | None = None
    capacity_type: str = "fixed"
    note: str | None = None


class HardwareInterfaceUpdate(BaseModel):
    interface_type: str | None = None
    speed: str | None = None
    count: int | None = None
    connector_type: str | None = None
    capacity_type: str | None = None
    note: str | None = None


class HardwareInterfaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    interface_type: str
    speed: str | None
    count: int
    connector_type: str | None
    capacity_type: str
    note: str | None

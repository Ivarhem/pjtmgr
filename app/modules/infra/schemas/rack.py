from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RackCreate(BaseModel):
    room_id: int
    rack_code: str | None = None
    rack_name: str | None = None
    total_units: int = 42
    location_detail: str | None = None
    is_active: bool = True
    note: str | None = None


class RackUpdate(BaseModel):
    rack_code: str | None = None
    rack_name: str | None = None
    total_units: int | None = None
    location_detail: str | None = None
    is_active: bool | None = None
    note: str | None = None


class RackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    room_code: str | None = None
    room_name: str | None = None
    center_code: str | None = None
    center_name: str | None = None
    rack_code: str
    rack_name: str | None = None
    total_units: int
    location_detail: str | None = None
    is_active: bool
    note: str | None = None
    created_at: datetime
    updated_at: datetime

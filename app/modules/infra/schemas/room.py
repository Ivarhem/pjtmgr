from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoomCreate(BaseModel):
    center_id: int
    room_code: str | None = None
    room_name: str
    floor: str | None = None
    is_active: bool = True
    note: str | None = None


class RoomUpdate(BaseModel):
    room_code: str | None = None
    room_name: str | None = None
    floor: str | None = None
    is_active: bool | None = None
    note: str | None = None


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    center_id: int
    center_code: str | None = None
    center_name: str | None = None
    room_code: str
    room_name: str
    floor: str | None = None
    is_active: bool
    note: str | None = None
    rack_count: int = 0
    created_at: datetime
    updated_at: datetime

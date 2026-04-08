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
    racks_per_row: int = 6
    prefix: str | None = None
    project_code: str | None = None
    grid_cols: int = 10
    grid_rows: int = 12


class RoomUpdate(BaseModel):
    room_code: str | None = None
    room_name: str | None = None
    floor: str | None = None
    is_active: bool | None = None
    note: str | None = None
    racks_per_row: int | None = None
    prefix: str | None = None
    project_code: str | None = None
    grid_cols: int | None = None
    grid_rows: int | None = None


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    center_id: int
    system_id: str | None = None
    center_code: str | None = None
    center_name: str | None = None
    room_code: str
    room_name: str
    floor: str | None = None
    is_active: bool
    note: str | None = None
    racks_per_row: int = 6
    rack_count: int = 0
    prefix: str | None = None
    project_code: str | None = None
    grid_cols: int = 10
    grid_rows: int = 12
    created_at: datetime
    updated_at: datetime

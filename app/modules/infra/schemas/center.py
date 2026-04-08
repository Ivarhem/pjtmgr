from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CenterCreate(BaseModel):
    partner_id: int
    center_code: str | None = None
    center_name: str
    location: str | None = None
    is_active: bool = True
    note: str | None = None
    prefix: str | None = None
    project_code: str | None = None


class CenterUpdate(BaseModel):
    center_code: str | None = None
    center_name: str | None = None
    location: str | None = None
    is_active: bool | None = None
    note: str | None = None
    prefix: str | None = None
    project_code: str | None = None


class CenterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_id: int
    system_id: str | None = None
    center_code: str
    center_name: str
    location: str | None = None
    is_active: bool
    note: str | None = None
    prefix: str | None = None
    project_code: str | None = None
    room_count: int = 0
    rack_count: int = 0
    created_at: datetime
    updated_at: datetime

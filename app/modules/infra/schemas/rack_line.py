from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RackLineCreate(BaseModel):
    line_name: str
    col_index: int | None = None
    slot_count: int
    disabled_slots: list[int] = []
    prefix: str | None = None
    start_col: int | None = None
    start_row: int | None = None
    end_col: int | None = None
    end_row: int | None = None
    direction: str | None = None


class RackLineUpdate(BaseModel):
    line_name: str | None = None
    col_index: int | None = None
    slot_count: int | None = None
    disabled_slots: list[int] | None = None
    prefix: str | None = None
    sort_order: int | None = None
    start_col: int | None = None
    start_row: int | None = None
    end_col: int | None = None
    end_row: int | None = None
    direction: str | None = None


class RackLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    line_name: str
    col_index: int | None
    slot_count: int
    disabled_slots: list[int]
    sort_order: int
    prefix: str | None = None
    start_col: int | None = None
    start_row: int | None = None
    end_col: int | None = None
    end_row: int | None = None
    direction: str | None = None
    racks: list[dict] = []
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PeriodDeliverableCreate(BaseModel):
    period_phase_id: int
    name: str
    description: str | None = None
    is_submitted: bool = False
    submitted_at: date | None = None
    note: str | None = None


class PeriodDeliverableUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_submitted: bool | None = None
    submitted_at: date | None = None
    note: str | None = None


class PeriodDeliverableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_phase_id: int
    name: str
    description: str | None
    is_submitted: bool
    submitted_at: date | None
    note: str | None
    created_at: datetime
    updated_at: datetime

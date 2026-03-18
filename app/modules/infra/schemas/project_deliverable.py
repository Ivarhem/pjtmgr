from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ProjectDeliverableCreate(BaseModel):
    project_phase_id: int
    name: str
    description: str | None = None
    is_submitted: bool = False
    submitted_at: date | None = None
    note: str | None = None


class ProjectDeliverableUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_submitted: bool | None = None
    submitted_at: date | None = None
    note: str | None = None


class ProjectDeliverableRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_phase_id: int
    name: str
    description: str | None
    is_submitted: bool
    submitted_at: date | None
    note: str | None
    created_at: datetime
    updated_at: datetime

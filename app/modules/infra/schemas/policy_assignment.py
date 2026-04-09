from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PolicyAssignmentCreate(BaseModel):
    partner_id: int
    asset_id: int | None = None
    policy_definition_id: int
    status: str = "not_checked"
    exception_reason: str | None = None
    checked_by: str | None = None
    checked_date: date | None = None
    evidence_note: str | None = None


class PolicyAssignmentUpdate(BaseModel):
    status: str | None = None
    exception_reason: str | None = None
    checked_by: str | None = None
    checked_date: date | None = None
    evidence_note: str | None = None


class PolicyAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_id: int
    asset_id: int | None
    policy_definition_id: int
    status: str
    exception_reason: str | None
    checked_by: str | None
    checked_date: date | None
    evidence_note: str | None
    created_at: datetime
    updated_at: datetime

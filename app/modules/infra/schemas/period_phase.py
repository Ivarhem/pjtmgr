from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PeriodPhaseCreate(BaseModel):
    contract_period_id: int
    phase_type: str
    task_scope: str | None = None
    deliverables_note: str | None = None
    cautions: str | None = None
    submission_required: bool = False
    submission_status: str = "pending"
    status: str = "not_started"


class PeriodPhaseUpdate(BaseModel):
    phase_type: str | None = None
    task_scope: str | None = None
    deliverables_note: str | None = None
    cautions: str | None = None
    submission_required: bool | None = None
    submission_status: str | None = None
    status: str | None = None


class PeriodPhaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_period_id: int
    phase_type: str
    task_scope: str | None
    deliverables_note: str | None
    cautions: str | None
    submission_required: bool
    submission_status: str
    status: str
    created_at: datetime
    updated_at: datetime

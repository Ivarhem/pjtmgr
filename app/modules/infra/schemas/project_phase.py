from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectPhaseCreate(BaseModel):
    project_id: int
    phase_type: str
    task_scope: str | None = None
    deliverables_note: str | None = None
    cautions: str | None = None
    submission_required: bool = False
    submission_status: str = "pending"
    status: str = "not_started"


class ProjectPhaseUpdate(BaseModel):
    phase_type: str | None = None
    task_scope: str | None = None
    deliverables_note: str | None = None
    cautions: str | None = None
    submission_required: bool | None = None
    submission_status: str | None = None
    status: str | None = None


class ProjectPhaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    phase_type: str
    task_scope: str | None
    deliverables_note: str | None
    cautions: str | None
    submission_required: bool
    submission_status: str
    status: str
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PeriodPartnerContactCreate(BaseModel):
    period_partner_id: int
    contact_id: int
    project_role: str
    note: str | None = None


class PeriodPartnerContactUpdate(BaseModel):
    project_role: str | None = None
    note: str | None = None


class PeriodPartnerContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_partner_id: int
    contact_id: int
    project_role: str
    note: str | None
    # enriched
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    created_at: datetime
    updated_at: datetime

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PeriodPartnerCreate(BaseModel):
    contract_period_id: int
    partner_id: int
    role: str
    scope_text: str | None = None
    note: str | None = None


class PeriodPartnerUpdate(BaseModel):
    role: str | None = None
    scope_text: str | None = None
    note: str | None = None


class PeriodPartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_period_id: int
    partner_id: int
    role: str
    scope_text: str | None
    note: str | None
    # enriched
    partner_name: str | None = None
    business_no: str | None = None
    created_at: datetime
    updated_at: datetime

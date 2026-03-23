from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PeriodCustomerContactCreate(BaseModel):
    period_customer_id: int
    contact_id: int
    project_role: str
    note: str | None = None


class PeriodCustomerContactUpdate(BaseModel):
    project_role: str | None = None
    note: str | None = None


class PeriodCustomerContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    period_customer_id: int
    contact_id: int
    project_role: str
    note: str | None
    # enriched
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    created_at: datetime
    updated_at: datetime

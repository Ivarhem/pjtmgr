from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCustomerCreate(BaseModel):
    project_id: int
    customer_id: int
    role: str
    scope_text: str | None = None
    note: str | None = None


class ProjectCustomerUpdate(BaseModel):
    role: str | None = None
    scope_text: str | None = None
    note: str | None = None


class ProjectCustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    customer_id: int
    role: str
    scope_text: str | None
    note: str | None
    # enriched
    customer_name: str | None = None
    business_no: str | None = None
    created_at: datetime
    updated_at: datetime

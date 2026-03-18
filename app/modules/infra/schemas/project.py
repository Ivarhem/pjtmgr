from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    project_code: str
    project_name: str
    customer_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    status: str = "planned"


class ProjectUpdate(BaseModel):
    project_code: str | None = None
    project_name: str | None = None
    customer_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    status: str | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_code: str
    project_name: str
    customer_id: int | None
    start_date: date | None
    end_date: date | None
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

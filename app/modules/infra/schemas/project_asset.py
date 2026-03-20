from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectAssetCreate(BaseModel):
    project_id: int
    asset_id: int
    role: str | None = None
    note: str | None = None


class ProjectAssetUpdate(BaseModel):
    role: str | None = None
    note: str | None = None


class ProjectAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    asset_id: int
    role: str | None
    note: str | None
    # enriched
    asset_name: str | None = None
    asset_type: str | None = None
    hostname: str | None = None
    project_code: str | None = None
    project_name: str | None = None
    created_at: datetime
    updated_at: datetime

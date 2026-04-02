from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetEventCreate(BaseModel):
    event_type: str
    summary: str
    detail: str | None = None
    occurred_at: datetime | None = None
    related_asset_id: int | None = None


class AssetEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int | None = None
    related_asset_id: int | None = None
    created_by_user_id: int | None = None
    event_type: str
    summary: str
    detail: str | None = None
    related_asset_name: str | None = None
    related_asset_code: str | None = None
    created_by_user_name: str | None = None
    asset_code_snapshot: str | None = None
    asset_name_snapshot: str | None = None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime

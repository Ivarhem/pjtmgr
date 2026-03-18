from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetContactCreate(BaseModel):
    asset_id: int
    contact_id: int
    role: str | None = None


class AssetContactUpdate(BaseModel):
    role: str | None = None


class AssetContactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    contact_id: int
    role: str | None
    created_at: datetime
    updated_at: datetime

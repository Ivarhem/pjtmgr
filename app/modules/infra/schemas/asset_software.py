from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetSoftwareCreate(BaseModel):
    asset_id: int = 0
    software_name: str
    version: str | None = None
    relation_type: str = "installed"
    note: str | None = None


class AssetSoftwareUpdate(BaseModel):
    software_name: str | None = None
    version: str | None = None
    relation_type: str | None = None
    note: str | None = None


class AssetSoftwareRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    software_name: str
    version: str | None
    relation_type: str
    note: str | None
    created_at: datetime
    updated_at: datetime

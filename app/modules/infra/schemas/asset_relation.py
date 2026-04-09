from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetRelationCreate(BaseModel):
    src_asset_id: int
    dst_asset_id: int
    relation_type: str
    note: str | None = None


class AssetRelationUpdate(BaseModel):
    relation_type: str | None = None
    note: str | None = None


class AssetRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    src_asset_id: int
    dst_asset_id: int
    relation_type: str
    note: str | None
    # enriched
    src_asset_name: str | None = None
    src_hostname: str | None = None
    dst_asset_name: str | None = None
    dst_hostname: str | None = None
    created_at: datetime
    updated_at: datetime

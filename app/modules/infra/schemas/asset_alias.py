from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AliasType(str, Enum):
    INTERNAL = "INTERNAL"
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    TEAM = "TEAM"
    LEGACY = "LEGACY"
    ETC = "ETC"


class AssetAliasCreate(BaseModel):
    asset_id: int
    alias_name: str
    alias_type: AliasType
    source_partner_id: int | None = None
    source_text: str | None = None
    note: str | None = None
    is_primary: bool = False


class AssetAliasUpdate(BaseModel):
    alias_name: str | None = None
    alias_type: AliasType | None = None
    source_partner_id: int | None = None
    source_text: str | None = None
    note: str | None = None
    is_primary: bool | None = None


class AssetAliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    alias_name: str
    alias_type: str
    source_partner_id: int | None
    source_text: str | None
    note: str | None
    is_primary: bool
    created_at: datetime
    updated_at: datetime

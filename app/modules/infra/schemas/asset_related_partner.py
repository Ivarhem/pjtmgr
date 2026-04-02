from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AssetRelatedPartnerCreate(BaseModel):
    asset_id: int
    partner_id: int
    relation_type: str
    is_primary: bool = False
    valid_from: date | None = None
    valid_to: date | None = None
    note: str | None = None


class AssetRelatedPartnerUpdate(BaseModel):
    relation_type: str | None = None
    is_primary: bool | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    note: str | None = None


class AssetRelatedPartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    partner_id: int
    partner_name: str | None = None
    partner_type: str | None = None
    partner_phone: str | None = None
    relation_type: str
    is_primary: bool
    valid_from: date | None = None
    valid_to: date | None = None
    note: str | None = None
    created_at: datetime
    updated_at: datetime

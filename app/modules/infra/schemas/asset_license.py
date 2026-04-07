from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AssetLicenseCreate(BaseModel):
    asset_id: int = 0
    license_type: str
    license_key: str | None = None
    licensed_to: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    note: str | None = None


class AssetLicenseUpdate(BaseModel):
    license_type: str | None = None
    license_key: str | None = None
    licensed_to: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    note: str | None = None


class AssetLicenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    license_type: str
    license_key: str | None
    licensed_to: str | None
    start_date: date | None
    end_date: date | None
    note: str | None
    created_at: datetime
    updated_at: datetime

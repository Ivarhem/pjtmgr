from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PeriodAssetCreate(BaseModel):
    contract_period_id: int
    asset_id: int
    role: str | None = None
    note: str | None = None


class PeriodAssetUpdate(BaseModel):
    role: str | None = None
    note: str | None = None


class PeriodAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contract_period_id: int
    asset_id: int
    role: str | None
    note: str | None
    # enriched
    asset_name: str | None = None
    hostname: str | None = None
    period_label: str | None = None
    created_at: datetime
    updated_at: datetime

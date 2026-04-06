from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AssetRoleReplacementAction(BaseModel):
    replacement_asset_id: int
    occurred_at: datetime | None = None
    note: str | None = None


class AssetRoleFailoverAction(BaseModel):
    replacement_asset_id: int
    occurred_at: datetime | None = None
    note: str | None = None


class AssetRoleRepurposeAction(BaseModel):
    new_role_name: str
    new_contract_period_id: int | None = None
    occurred_at: datetime | None = None
    note: str | None = None


class AssetRoleActionResult(BaseModel):
    source_role_id: int
    source_assignment_id: int | None = None
    target_role_id: int | None = None
    target_assignment_id: int | None = None
    message: str

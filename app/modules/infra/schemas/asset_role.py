from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AssetRoleCreate(BaseModel):
    partner_id: int
    contract_period_id: int | None = None
    role_name: str
    status: str = "active"
    note: str | None = None


class AssetRoleUpdate(BaseModel):
    contract_period_id: int | None = None
    role_name: str | None = None
    status: str | None = None
    note: str | None = None


class AssetRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_id: int
    contract_period_id: int | None = None
    role_name: str
    status: str
    note: str | None = None
    current_asset_id: int | None = None
    current_asset_name: str | None = None
    current_asset_code: str | None = None
    current_asset_status: str | None = None
    current_assignment_id: int | None = None
    current_asset_domain: str | None = None
    current_asset_center_label: str | None = None
    current_asset_product_family: str | None = None
    current_asset_vendor: str | None = None
    created_at: datetime
    updated_at: datetime


class AssetRoleAssignmentCreate(BaseModel):
    asset_id: int
    assignment_type: str = "primary"
    valid_from: date | None = None
    valid_to: date | None = None
    is_current: bool = True
    note: str | None = None


class AssetRoleAssignmentUpdate(BaseModel):
    assignment_type: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    is_current: bool | None = None
    note: str | None = None


class AssetRoleAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_role_id: int
    asset_id: int
    asset_name: str | None = None
    asset_code: str | None = None
    asset_status: str | None = None
    assignment_type: str
    valid_from: date | None = None
    valid_to: date | None = None
    is_current: bool
    note: str | None = None
    created_at: datetime
    updated_at: datetime

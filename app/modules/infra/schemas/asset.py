from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AssetCreate(BaseModel):
    partner_id: int
    hardware_model_id: int          # 필수 — 카탈로그 제품
    project_asset_number: str | None = None
    customer_asset_number: str | None = None
    asset_name: str
    hostname: str | None = None
    period_id: int | None = None    # 귀속사업 (선택)
    center_id: int | None = None
    room_id: int | None = None
    rack_id: int | None = None


class AssetUpdate(BaseModel):
    period_id: int | None = None
    partner_id: int | None = None
    asset_code: str | None = None
    project_asset_number: str | None = None
    customer_asset_number: str | None = None
    asset_name: str | None = None
    vendor: str | None = None
    model: str | None = None
    role: str | None = None
    environment: str | None = None
    location: str | None = None
    status: str | None = None
    note: str | None = None
    hardware_model_id: int | None = None
    # Equipment Spec
    center_id: int | None = None
    room_id: int | None = None
    rack_id: int | None = None
    center: str | None = None
    operation_type: str | None = None
    equipment_id: str | None = None
    rack_no: str | None = None
    rack_unit: str | None = None
    phase: str | None = None
    received_date: date | None = None
    category: str | None = None
    subcategory: str | None = None
    serial_no: str | None = None
    # Logical Config
    hostname: str | None = None
    cluster: str | None = None
    service_name: str | None = None
    zone: str | None = None
    service_ip: str | None = None
    mgmt_ip: str | None = None
    # Hardware Config
    size_unit: int | None = None
    lc_count: int | None = None
    ha_count: int | None = None
    utp_count: int | None = None
    power_count: int | None = None
    power_type: str | None = None
    firmware_version: str | None = None
    # Asset Info
    asset_class: str | None = None
    asset_number: str | None = None
    year_acquired: int | None = None
    dept: str | None = None
    primary_contact_name: str | None = None
    secondary_contact_name: str | None = None
    maintenance_vendor: str | None = None


class AssetCurrentRoleUpdate(BaseModel):
    asset_role_id: int | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_id: int
    asset_code: str | None = None
    project_asset_number: str | None = None
    customer_asset_number: str | None = None
    asset_name: str
    vendor: str | None
    model: str | None
    role: str | None
    environment: str
    location: str | None
    status: str
    note: str | None
    hardware_model_id: int | None = None
    # Equipment Spec
    center_id: int | None = None
    room_id: int | None = None
    rack_id: int | None = None
    center_label: str | None = None
    room_label: str | None = None
    rack_label: str | None = None
    center_is_fallback_text: bool = False
    rack_is_fallback_text: bool = False
    center: str | None = None
    operation_type: str | None = None
    equipment_id: str | None = None
    rack_no: str | None = None
    rack_unit: str | None = None
    phase: str | None = None
    received_date: date | None = None
    category: str | None = None
    subcategory: str | None = None
    serial_no: str | None = None
    # Logical Config
    hostname: str | None = None
    cluster: str | None = None
    service_name: str | None = None
    zone: str | None = None
    service_ip: str | None = None
    mgmt_ip: str | None = None
    # Hardware Config
    size_unit: int | None = None
    lc_count: int | None = None
    ha_count: int | None = None
    utp_count: int | None = None
    power_count: int | None = None
    power_type: str | None = None
    firmware_version: str | None = None
    # Asset Info
    asset_class: str | None = None
    asset_number: str | None = None
    year_acquired: int | None = None
    dept: str | None = None
    primary_contact_name: str | None = None
    secondary_contact_name: str | None = None
    maintenance_vendor: str | None = None
    # Enriched fields (inventory view)
    period_id: int | None = None
    period_label: str | None = None
    contract_name: str | None = None
    classification_path: str | None = None
    classification_is_fallback_text: bool = False
    classification_level_1_name: str | None = None
    classification_level_2_name: str | None = None
    classification_level_3_name: str | None = None
    classification_level_4_name: str | None = None
    classification_level_5_name: str | None = None
    catalog_kind: str | None = None
    current_role_names: list[str] = []
    current_role_id: int | None = None
    aliases: list[str] = []
    created_at: datetime
    updated_at: datetime

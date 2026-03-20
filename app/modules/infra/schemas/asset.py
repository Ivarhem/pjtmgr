from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AssetCreate(BaseModel):
    project_id: int
    asset_code: str | None = None
    asset_name: str
    asset_type: str
    vendor: str | None = None
    model: str | None = None
    role: str | None = None
    environment: str = "prod"
    location: str | None = None
    status: str = "planned"
    note: str | None = None
    # Equipment Spec
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


class AssetUpdate(BaseModel):
    project_id: int | None = None
    asset_code: str | None = None
    asset_name: str | None = None
    asset_type: str | None = None
    vendor: str | None = None
    model: str | None = None
    role: str | None = None
    environment: str | None = None
    location: str | None = None
    status: str | None = None
    note: str | None = None
    # Equipment Spec
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


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    asset_code: str | None = None
    asset_name: str
    asset_type: str
    vendor: str | None
    model: str | None
    role: str | None
    environment: str
    location: str | None
    status: str
    note: str | None
    # Equipment Spec
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
    project_code: str | None = None
    project_name: str | None = None
    created_at: datetime
    updated_at: datetime

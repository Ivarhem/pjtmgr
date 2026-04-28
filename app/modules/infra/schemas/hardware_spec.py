from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HardwareSpecCreate(BaseModel):
    size_unit: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    depth_mm: int | None = None
    weight_kg: float | None = None
    power_count: int | None = None
    power_type: str | None = None
    power_watt: int | None = None
    power_summary: str | None = None
    cpu_summary: str | None = None
    memory_summary: str | None = None
    storage_summary: str | None = None
    throughput_summary: str | None = None
    os_firmware: str | None = None
    spec_url: str | None = None


class HardwareSpecUpdate(BaseModel):
    size_unit: int | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    depth_mm: int | None = None
    weight_kg: float | None = None
    power_count: int | None = None
    power_type: str | None = None
    power_watt: int | None = None
    power_summary: str | None = None
    cpu_summary: str | None = None
    memory_summary: str | None = None
    storage_summary: str | None = None
    throughput_summary: str | None = None
    os_firmware: str | None = None
    spec_url: str | None = None


class HardwareSpecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    size_unit: int | None
    width_mm: int | None
    height_mm: int | None
    depth_mm: int | None
    weight_kg: float | None
    power_count: int | None
    power_type: str | None
    power_watt: int | None
    power_summary: str | None
    cpu_summary: str | None
    memory_summary: str | None
    storage_summary: str | None
    throughput_summary: str | None
    os_firmware: str | None
    spec_url: str | None

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.infra.schemas.hardware_spec import HardwareSpecRead
from app.modules.infra.schemas.hardware_interface import HardwareInterfaceRead


class ProductCatalogCreate(BaseModel):
    vendor: str
    name: str
    product_type: str = "hardware"
    category: str
    eos_date: date | None = None
    eosl_date: date | None = None
    eosl_note: str | None = None
    reference_url: str | None = None


class ProductCatalogUpdate(BaseModel):
    vendor: str | None = None
    name: str | None = None
    product_type: str | None = None
    category: str | None = None
    eos_date: date | None = None
    eosl_date: date | None = None
    eosl_note: str | None = None
    reference_url: str | None = None


class ProductCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    name: str
    product_type: str
    category: str
    eos_date: date | None
    eosl_date: date | None
    eosl_note: str | None
    reference_url: str | None
    created_at: datetime
    updated_at: datetime


class ProductCatalogDetail(ProductCatalogRead):
    """상세 조회 시 nested spec + interfaces 포함."""
    hardware_spec: HardwareSpecRead | None = None
    interfaces: list[HardwareInterfaceRead] = []

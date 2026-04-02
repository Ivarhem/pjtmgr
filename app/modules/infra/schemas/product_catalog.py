from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.infra.schemas.hardware_spec import HardwareSpecRead
from app.modules.infra.schemas.hardware_interface import HardwareInterfaceRead
from app.modules.infra.schemas.software_spec import SoftwareSpecRead
from app.modules.infra.schemas.model_spec import ModelSpecRead
from app.modules.infra.schemas.generic_catalog_profile import GenericCatalogProfileRead
from app.modules.infra.schemas.product_catalog_attribute_value import (
    ProductCatalogAttributeValueRead,
    ProductCatalogAttributeValueWrite,
)


class ProductCatalogCreate(BaseModel):
    vendor: str
    name: str
    product_type: str = "hardware"
    version: str | None = None
    eos_date: date | None = None
    eosl_date: date | None = None
    eosl_note: str | None = None
    reference_url: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    source_confidence: str | None = None
    last_verified_at: datetime | None = None
    verification_status: str | None = None
    import_batch_id: str | None = None
    attributes: list[ProductCatalogAttributeValueWrite] | None = None


class ProductCatalogUpdate(BaseModel):
    vendor: str | None = None
    name: str | None = None
    product_type: str | None = None
    version: str | None = None
    eos_date: date | None = None
    eosl_date: date | None = None
    eosl_note: str | None = None
    reference_url: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    source_confidence: str | None = None
    last_verified_at: datetime | None = None
    verification_status: str | None = None
    import_batch_id: str | None = None
    attributes: list[ProductCatalogAttributeValueWrite] | None = None


class ProductCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    name: str
    product_type: str
    version: str | None
    eos_date: date | None
    eosl_date: date | None
    eosl_note: str | None
    reference_url: str | None
    source_name: str | None
    source_url: str | None
    source_confidence: str | None
    last_verified_at: datetime | None
    verification_status: str | None
    import_batch_id: str | None
    attributes: list[ProductCatalogAttributeValueRead] = []
    classification_level_1_name: str | None = None
    classification_level_2_name: str | None = None
    classification_level_3_name: str | None = None
    classification_level_4_name: str | None = None
    classification_level_5_name: str | None = None
    is_placeholder: bool
    created_at: datetime
    updated_at: datetime


class ProductCatalogDetail(ProductCatalogRead):
    """상세 조회 시 nested spec + interfaces 포함."""
    hardware_spec: HardwareSpecRead | None = None
    software_spec: SoftwareSpecRead | None = None
    model_spec: ModelSpecRead | None = None
    generic_profile: GenericCatalogProfileRead | None = None
    interfaces: list[HardwareInterfaceRead] = []


class ProductCatalogBulkUpsertRow(BaseModel):
    product_id: int | None = None
    vendor: str
    name: str
    product_type: str = "hardware"
    version: str | None = None
    domain: str | None = None
    imp_type: str | None = None
    product_family: str | None = None
    platform: str | None = None
    reference_url: str | None = None
    eos_date: date | None = None
    eosl_date: date | None = None
    eosl_note: str | None = None


class ProductCatalogBulkUpsertRequest(BaseModel):
    rows: list[ProductCatalogBulkUpsertRow]


class ProductCatalogBulkUpsertRowResult(BaseModel):
    row_no: int
    action: str
    product_id: int | None = None
    vendor: str | None = None
    name: str | None = None
    status: str = "ok"
    message: str | None = None


class ProductCatalogBulkUpsertResponse(BaseModel):
    total: int
    created: int
    updated: int
    failed: int
    rows: list[ProductCatalogBulkUpsertRowResult]

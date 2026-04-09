from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.modules.infra.schemas.hardware_spec import HardwareSpecRead
from app.modules.infra.schemas.hardware_interface import HardwareInterfaceRead
from app.modules.infra.schemas.software_spec import SoftwareSpecRead
from app.modules.infra.schemas.model_spec import ModelSpecRead
from app.modules.infra.schemas.generic_catalog_profile import GenericCatalogProfileRead


class ProductCatalogCreate(BaseModel):
    vendor: str
    name: str
    product_type: str = "hardware"
    version: str | None = None
    category: str | None = None
    classification_node_code: str | None = None
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


class ProductCatalogUpdate(BaseModel):
    vendor: str | None = None
    name: str | None = None
    product_type: str | None = None
    version: str | None = None
    category: str | None = None
    classification_node_code: str | None = None
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


class ProductCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    name: str
    product_type: str
    version: str | None
    category: str
    classification_node_code: str | None
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
    asset_type_key: str | None = None
    asset_type_code: str | None = None
    asset_type_label: str | None = None
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

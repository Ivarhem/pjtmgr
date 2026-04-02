from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class GenericCatalogProfileCreate(BaseModel):
    owner_scope: str | None = None
    service_level: str | None = None
    criticality: str | None = None
    exposure_scope: str | None = None
    data_classification: str | None = None
    default_runtime: str | None = None
    summary_note: str | None = None


class GenericCatalogProfileUpdate(BaseModel):
    owner_scope: str | None = None
    service_level: str | None = None
    criticality: str | None = None
    exposure_scope: str | None = None
    data_classification: str | None = None
    default_runtime: str | None = None
    summary_note: str | None = None


class GenericCatalogProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    owner_scope: str | None
    service_level: str | None
    criticality: str | None
    exposure_scope: str | None
    data_classification: str | None
    default_runtime: str | None
    summary_note: str | None

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ProductCatalogResearchRequest(BaseModel):
    fill_only: bool = True
    force: bool = False


class ProductCatalogBatchResearchRequest(BaseModel):
    limit: int = 5
    fill_only: bool = True
    force: bool = False
    include_pending_review: bool = False


class ProductCatalogResearchResponse(BaseModel):
    product_id: int
    vendor: str
    name: str
    mode: str
    confidence: str | None = None
    spec_candidates: int = 0
    spec_applied: int = 0
    eosl_candidates: int = 0
    eosl_applied: int = 0
    interfaces_created: int = 0
    interface_candidates: int = 0
    interfaces_skipped: int = 0
    uncertain_fields: list[str] = []
    eos_date: date | None = None
    eosl_date: date | None = None
    spec_url: str | None = None
    sku_expansion_candidates: list[str] = []
    sku_expansion_created: int = 0
    sku_research_results: list[dict] = []
    message: str
    skipped: bool = False
    skip_reason: str | None = None


class ProductCatalogBatchResearchResponse(BaseModel):
    requested_limit: int
    selected: int
    success: int = 0
    skipped: int = 0
    failed: int = 0
    rows: list[dict] = []


class ProductCatalogSkuExpansionPreviewResponse(BaseModel):
    product_id: int
    vendor: str
    name: str
    model_family: str | None = None
    is_family_level: bool = False
    candidates: list[str] = []
    delete_family_default: bool = True
    message: str


class ProductCatalogSkuExpansionApplyRequest(BaseModel):
    selected_names: list[str] | None = None
    delete_family: bool = True


class ProductCatalogSkuExpansionApplyResponse(BaseModel):
    product_id: int
    vendor: str
    name: str
    model_family: str | None = None
    created: int = 0
    created_products: list[dict] = []
    skipped_existing: list[str] = []
    deleted_family: bool = False
    message: str

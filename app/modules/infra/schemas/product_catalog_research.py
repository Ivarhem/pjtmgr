from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ProductCatalogResearchRequest(BaseModel):
    fill_only: bool = True


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
    message: str

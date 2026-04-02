from __future__ import annotations

from pydantic import BaseModel


class CatalogVendorBulkUpsertRow(BaseModel):
    source_vendor: str | None = None
    canonical_vendor: str
    aliases: list[str] = []
    apply_to_products: bool = True
    is_active: bool = True


class CatalogVendorBulkUpsertRequest(BaseModel):
    rows: list[CatalogVendorBulkUpsertRow]


class CatalogVendorBulkUpsertRowResult(BaseModel):
    row_no: int
    canonical_vendor: str
    status: str = "ok"
    action: str
    message: str | None = None


class CatalogVendorBulkUpsertResponse(BaseModel):
    total: int
    updated: int
    failed: int
    rows: list[CatalogVendorBulkUpsertRowResult]

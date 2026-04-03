from __future__ import annotations

from pydantic import BaseModel


class CatalogVendorAliasItem(BaseModel):
    id: int
    alias_value: str
    normalized_alias: str
    is_active: bool


class CatalogVendorSummary(BaseModel):
    vendor: str
    product_count: int
    alias_count: int
    aliases: list[CatalogVendorAliasItem]
    name_ko: str | None = None
    memo: str | None = None


class CatalogVendorBulkUpsertRow(BaseModel):
    source_vendor: str | None = None
    canonical_vendor: str
    aliases: list[str] = []
    apply_to_products: bool = True
    is_active: bool = True
    name_ko: str | None = None
    memo: str | None = None


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

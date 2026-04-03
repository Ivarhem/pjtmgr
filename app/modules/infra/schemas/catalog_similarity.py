from __future__ import annotations

from pydantic import BaseModel


class CatalogSimilarityCheckRequest(BaseModel):
    vendor: str
    name: str
    exclude_product_id: int | None = None


class CatalogSimilarityCandidate(BaseModel):
    id: int
    vendor: str
    name: str
    score: int
    exact_normalized: bool = False
    asset_count: int = 0


class CatalogSimilarityCheckResponse(BaseModel):
    normalized_vendor: str
    normalized_name: str
    exact_matches: list[CatalogSimilarityCandidate]
    similar_matches: list[CatalogSimilarityCandidate]


class ProductMergeRequest(BaseModel):
    source_id: int
    target_id: int


class ProductMergeResponse(BaseModel):
    merged_asset_count: int
    source_vendor: str
    source_name: str
    target_vendor: str
    target_name: str


class ProductDismissRequest(BaseModel):
    product_id_a: int
    product_id_b: int


class ProductRestoreRequest(BaseModel):
    product_id_a: int
    product_id_b: int

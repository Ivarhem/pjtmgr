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


class CatalogSimilarityCheckResponse(BaseModel):
    normalized_vendor: str
    normalized_name: str
    exact_matches: list[CatalogSimilarityCandidate]
    similar_matches: list[CatalogSimilarityCandidate]

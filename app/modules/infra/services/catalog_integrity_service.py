from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.services.catalog_alias_service import (
    get_attribute_option_alias,
    list_attribute_option_aliases,
    list_vendor_alias_summaries,
)
from app.modules.infra.services.catalog_similarity_service import (
    score_product_similarity,
    tokenize_product_name,
)


def list_catalog_vendor_integrity(db: Session, q: str | None = None) -> list[dict]:
    return list_vendor_alias_summaries(db, q=q)


def list_catalog_attribute_alias_integrity(
    db: Session,
    *,
    attribute_key: str | None = None,
    q: str | None = None,
    active_only: bool = False,
) -> list[dict]:
    return list_attribute_option_aliases(db, attribute_key=attribute_key, q=q, active_only=active_only)


def get_catalog_attribute_alias_integrity(db: Session, alias_id: int) -> dict:
    return get_attribute_option_alias(db, alias_id)


def list_similar_catalog_products(
    db: Session,
    *,
    q: str | None = None,
    min_score: int = 75,
    limit: int = 200,
) -> list[dict]:
    stmt = select(ProductCatalog).order_by(ProductCatalog.vendor.asc(), ProductCatalog.name.asc(), ProductCatalog.id.asc())
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where((ProductCatalog.vendor.ilike(like)) | (ProductCatalog.name.ilike(like)))
    products = list(db.scalars(stmt))
    rows: list[dict] = []
    seen_pairs: set[tuple[int, int]] = set()

    for idx, base in enumerate(products):
        source_tokens = tokenize_product_name(base.name)
        for candidate in products[idx + 1:]:
            pair_key = (base.id, candidate.id)
            if pair_key in seen_pairs:
                continue
            score = score_product_similarity(
                normalized_vendor=base.normalized_vendor or "",
                normalized_name=base.normalized_name or "",
                source_tokens=source_tokens,
                candidate=candidate,
            )
            if score < min_score:
                continue
            rows.append(
                {
                    "base_id": base.id,
                    "base_vendor": base.vendor,
                    "base_name": base.name,
                    "candidate_id": candidate.id,
                    "candidate_vendor": candidate.vendor,
                    "candidate_name": candidate.name,
                    "normalized_vendor": base.normalized_vendor or "",
                    "normalized_name": base.normalized_name or "",
                    "score": score,
                }
            )
            seen_pairs.add(pair_key)

    rows.sort(key=lambda item: (-item["score"], item["base_vendor"], item["base_name"], item["candidate_name"]))
    return rows[:limit]

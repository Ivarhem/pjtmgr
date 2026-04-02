from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.infra.models.product_catalog import ProductCatalog


_SEPARATOR_RE = re.compile(r"[\s\-_./(),]+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z가-힣]+")
_TOKEN_RE = re.compile(r"[a-z]+[0-9a-z]*|[0-9]+[a-z]*|[가-힣]+", re.IGNORECASE)
_PRODUCT_SYNONYMS = {
    "catalyst": "cat",
}


def normalize_vendor_name(vendor: str | None) -> str:
    return _normalize_text(vendor)


def normalize_product_name(name: str | None) -> str:
    normalized = _normalize_text(name)
    if not normalized:
        return ""
    return normalized


def tokenize_product_name(name: str | None) -> list[str]:
    normalized = unicodedata.normalize("NFKC", name or "").lower().strip()
    if not normalized:
        return []
    collapsed = _SEPARATOR_RE.sub(" ", normalized)
    tokens = _TOKEN_RE.findall(collapsed)
    result: list[str] = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        token = _PRODUCT_SYNONYMS.get(token, token)
        result.append(token)
    return result


def find_similar_products(
    db: Session,
    *,
    vendor: str,
    name: str,
    exclude_product_id: int | None = None,
    limit: int = 5,
) -> dict:
    normalized_vendor = normalize_vendor_name(vendor)
    normalized_name = normalize_product_name(name)
    tokens = tokenize_product_name(name)
    stmt = select(ProductCatalog).order_by(ProductCatalog.vendor.asc(), ProductCatalog.name.asc())
    candidates = list(db.scalars(stmt))
    exact_matches: list[dict] = []
    similar_matches: list[dict] = []
    for candidate in candidates:
        if exclude_product_id is not None and candidate.id == exclude_product_id:
            continue
        score = score_product_similarity(
            normalized_vendor=normalized_vendor,
            normalized_name=normalized_name,
            source_tokens=tokens,
            candidate=candidate,
        )
        if score <= 0:
            continue
        payload = {
            "id": candidate.id,
            "vendor": candidate.vendor,
            "name": candidate.name,
            "score": score,
            "exact_normalized": bool(
                normalized_vendor
                and normalized_name
                and candidate.normalized_vendor == normalized_vendor
                and candidate.normalized_name == normalized_name
            ),
        }
        if payload["exact_normalized"]:
            exact_matches.append(payload)
        elif score >= 75:
            similar_matches.append(payload)
    exact_matches.sort(key=lambda item: (-item["score"], item["vendor"], item["name"], item["id"]))
    similar_matches.sort(key=lambda item: (-item["score"], item["vendor"], item["name"], item["id"]))
    return {
        "normalized_vendor": normalized_vendor,
        "normalized_name": normalized_name,
        "exact_matches": exact_matches[:limit],
        "similar_matches": similar_matches[:limit],
    }


def score_product_similarity(
    *,
    normalized_vendor: str,
    normalized_name: str,
    source_tokens: list[str],
    candidate: ProductCatalog,
) -> int:
    candidate_vendor = candidate.normalized_vendor or normalize_vendor_name(candidate.vendor)
    candidate_name = candidate.normalized_name or normalize_product_name(candidate.name)
    candidate_tokens = tokenize_product_name(candidate.name)
    if normalized_vendor and normalized_name and candidate_vendor == normalized_vendor and candidate_name == normalized_name:
        return 100

    score = 0
    if normalized_vendor and candidate_vendor == normalized_vendor:
        score += 35
    elif (
        normalized_vendor
        and candidate_vendor
        and (normalized_vendor in candidate_vendor or candidate_vendor in normalized_vendor)
    ):
        score += 15

    if normalized_name and candidate_name:
        if normalized_name == candidate_name:
            score += 55
        elif normalized_name in candidate_name or candidate_name in normalized_name:
            score += 25

    if source_tokens and candidate_tokens:
        overlap = set(source_tokens).intersection(candidate_tokens)
        if overlap:
            token_score = round((len(overlap) / max(len(set(source_tokens)), len(set(candidate_tokens)))) * 60)
            score += token_score
        digit_overlap = [token for token in overlap if any(ch.isdigit() for ch in token)]
        if len(digit_overlap) >= 2:
            score += 15

    return min(score, 99)


def build_normalized_catalog_fields(vendor: str | None, name: str | None) -> dict[str, str]:
    return {
        "normalized_vendor": normalize_vendor_name(vendor),
        "normalized_name": normalize_product_name(name),
    }


def _normalize_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").lower().strip()
    if not normalized:
        return ""
    normalized = _SEPARATOR_RE.sub("", normalized)
    normalized = _NON_ALNUM_RE.sub("", normalized)
    return normalized

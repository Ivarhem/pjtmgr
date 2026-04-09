from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.infra.models.product_catalog import ProductCatalog


def enrich_catalog_preview_rows(
    db: Session,
    domain: str,
    preview_rows: list[dict],
    parsed_rows: list[dict],
    on_duplicate: str,
) -> list[dict]:
    if domain not in {"spec", "eosl", "software", "model"}:
        return preview_rows

    existing = _build_catalog_lookup(db)
    enriched_rows: list[dict] = []

    for index, row in enumerate(preview_rows):
        parsed = parsed_rows[index] if index < len(parsed_rows) else {}
        vendor = parsed.get("vendor") or row.get("vendor")
        name = parsed.get("name") or row.get("name")
        matched = existing.get((vendor, name)) if vendor and name else None

        status = "invalid"
        status_label = "검증오류"

        if row.get("errors"):
            status = "invalid"
            status_label = "검증오류"
        elif domain in {"spec", "software", "model"}:
            if matched is None:
                status = "new"
                status_label = "신규"
            elif on_duplicate == "overwrite":
                status = "update"
                status_label = "갱신예정"
            else:
                status = "skip_existing"
                status_label = "기존존재"
        elif domain == "eosl":
            if matched is None:
                status = "unmatched"
                status_label = "미매칭"
            else:
                changed = any(
                    not _is_same_value(getattr(matched, field), parsed.get(field))
                    for field in ("eos_date", "eosl_date", "eosl_note")
                    if parsed.get(field) is not None
                )
                if changed:
                    status = "update"
                    status_label = "갱신예정"
                else:
                    status = "unchanged"
                    status_label = "변경없음"

        enriched = dict(row)
        enriched["status"] = status
        enriched["status_label"] = status_label
        enriched["matched_product_id"] = matched.id if matched is not None else None
        enriched_rows.append(enriched)

    return enriched_rows


def _build_catalog_lookup(db: Session) -> dict[tuple[str, str], ProductCatalog]:
    return {
        (product.vendor, product.name): product
        for product in db.scalars(select(ProductCatalog))
    }


def _is_same_value(left, right) -> bool:
    if left is None and right in ("", None):
        return True
    if right is None and left in ("", None):
        return True
    return left == right

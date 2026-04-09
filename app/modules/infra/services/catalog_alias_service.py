from __future__ import annotations

import re
import unicodedata

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_manage_catalog_taxonomy
from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.user import User
from app.modules.infra.models.catalog_attribute_def import CatalogAttributeDef
from app.modules.infra.models.catalog_attribute_option import CatalogAttributeOption
from app.modules.infra.models.catalog_attribute_option_alias import CatalogAttributeOptionAlias
from app.modules.infra.models.catalog_vendor_alias import CatalogVendorAlias
from app.modules.infra.models.catalog_vendor_meta import CatalogVendorMeta
from app.modules.infra.models.product_catalog_attribute_value import ProductCatalogAttributeValue
from app.modules.infra.schemas.catalog_attribute_option_alias import (
    CatalogAttributeOptionAliasCreate,
    CatalogAttributeOptionAliasUpdate,
)
from app.modules.infra.schemas.catalog_vendor_management import CatalogVendorBulkUpsertRow
from app.modules.infra.services.catalog_similarity_service import normalize_vendor_name

_SEPARATOR_RE = re.compile(r"[\s\-_./(),]+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z가-힣]+")


def normalize_catalog_alias(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").lower().strip()
    if not normalized:
        return ""
    normalized = _SEPARATOR_RE.sub("", normalized)
    normalized = _NON_ALNUM_RE.sub("", normalized)
    return normalized


def resolve_vendor_canonical(db: Session, vendor: str | None) -> str | None:
    if vendor is None:
        return None
    cleaned = vendor.strip()
    if not cleaned:
        return None
    normalized = normalize_vendor_name(cleaned)
    if not normalized:
        return cleaned
    alias = db.scalar(
        select(CatalogVendorAlias)
        .where(
            CatalogVendorAlias.normalized_alias == normalized,
            CatalogVendorAlias.is_active.is_(True),
        )
        .order_by(CatalogVendorAlias.sort_order.asc(), CatalogVendorAlias.id.asc())
    )
    return alias.vendor_canonical if alias else cleaned


def resolve_attribute_option_canonical(
    db: Session,
    *,
    attribute_key: str,
    option_key: str | None = None,
    raw_value: str | None = None,
) -> CatalogAttributeOption | None:
    attribute = db.scalar(
        select(CatalogAttributeDef).where(
            CatalogAttributeDef.attribute_key == attribute_key,
            CatalogAttributeDef.is_active.is_(True),
        )
    )
    if attribute is None:
        return None

    candidates = [option_key, raw_value]
    for candidate in candidates:
        cleaned = (candidate or "").strip()
        if not cleaned:
            continue
        exact_option = db.scalar(
            select(CatalogAttributeOption).where(
                CatalogAttributeOption.attribute_id == attribute.id,
                CatalogAttributeOption.option_key == cleaned,
                CatalogAttributeOption.is_active.is_(True),
            )
        )
        if exact_option is not None:
            return exact_option
        exact_label = db.scalar(
            select(CatalogAttributeOption).where(
                CatalogAttributeOption.attribute_id == attribute.id,
                CatalogAttributeOption.label == cleaned,
                CatalogAttributeOption.is_active.is_(True),
            )
        )
        if exact_label is not None:
            return exact_label
        normalized = normalize_catalog_alias(cleaned)
        if not normalized:
            continue
        alias = db.scalar(
            select(CatalogAttributeOptionAlias)
            .join(CatalogAttributeOption, CatalogAttributeOption.id == CatalogAttributeOptionAlias.attribute_option_id)
            .where(
                CatalogAttributeOption.attribute_id == attribute.id,
                CatalogAttributeOptionAlias.normalized_alias == normalized,
                CatalogAttributeOptionAlias.is_active.is_(True),
                CatalogAttributeOption.is_active.is_(True),
            )
            .order_by(CatalogAttributeOptionAlias.sort_order.asc(), CatalogAttributeOptionAlias.id.asc())
        )
        if alias is not None:
            return alias.attribute_option
    return None


def list_vendor_alias_summaries(db: Session, q: str | None = None) -> list[dict]:
    from app.modules.infra.models.product_catalog import ProductCatalog

    # 1) ProductCatalog 기반 제조사 + 제품 수
    product_stmt = (
        select(
            ProductCatalog.vendor.label("vendor"),
            func.count(ProductCatalog.id).label("product_count"),
        )
        .group_by(ProductCatalog.vendor)
    )
    if q:
        like = f"%{q.strip()}%"
        alias_vendors = db.scalars(
            select(CatalogVendorAlias.vendor_canonical).where(
                CatalogVendorAlias.alias_value.ilike(like),
                CatalogVendorAlias.is_active.is_(True),
            )
        ).all()
        product_stmt = product_stmt.where(
            ProductCatalog.vendor.ilike(like)
            | ProductCatalog.vendor.in_(alias_vendors)
        )
    vendor_product_map: dict[str, int] = {}
    for row in db.execute(product_stmt).mappings().all():
        vendor_product_map[row["vendor"]] = int(row["product_count"] or 0)

    # similar_count > 0인 제품 수 (제조사별)
    similar_stmt = (
        select(
            ProductCatalog.vendor.label("vendor"),
            func.count(ProductCatalog.id).label("similar_product_count"),
        )
        .where(ProductCatalog.similar_count > 0)
        .group_by(ProductCatalog.vendor)
    )
    vendor_similar_map: dict[str, int] = {}
    for row in db.execute(similar_stmt).mappings().all():
        vendor_similar_map[row["vendor"]] = int(row["similar_product_count"] or 0)

    # 2) CatalogVendorAlias 기반 alias 정보
    alias_stmt = (
        select(
            CatalogVendorAlias.id,
            CatalogVendorAlias.vendor_canonical,
            CatalogVendorAlias.alias_value,
            CatalogVendorAlias.normalized_alias,
            CatalogVendorAlias.is_active,
        )
        .where(CatalogVendorAlias.is_active.is_(True))
        .order_by(CatalogVendorAlias.vendor_canonical.asc(), CatalogVendorAlias.sort_order.asc())
    )
    alias_map: dict[str, list[dict]] = {}
    for row in db.execute(alias_stmt).mappings().all():
        alias_map.setdefault(row["vendor_canonical"], []).append(
            {
                "id": row["id"],
                "alias_value": row["alias_value"],
                "normalized_alias": row["normalized_alias"],
                "is_active": row["is_active"],
            }
        )

    # 3) 메타 정보 (한글명, 메모)
    meta_rows = db.execute(
        select(CatalogVendorMeta.vendor_canonical, CatalogVendorMeta.name_ko, CatalogVendorMeta.memo)
    ).mappings().all()
    meta_map: dict[str, dict] = {
        row["vendor_canonical"]: {"name_ko": row["name_ko"], "memo": row["memo"]}
        for row in meta_rows
    }

    # 4) 두 소스를 합쳐 전체 제조사 목록 구성
    all_vendors = set(vendor_product_map.keys()) | set(alias_map.keys()) | set(meta_map.keys())
    if q:
        like_lower = q.strip().lower()
        all_vendors = {
            v for v in all_vendors
            if like_lower in (v or "").lower()
            or like_lower in (meta_map.get(v, {}).get("name_ko") or "").lower()
            or any(like_lower in a["alias_value"].lower() for a in alias_map.get(v, []))
        }

    results: list[dict] = []
    for vendor in all_vendors:
        all_aliases = alias_map.get(vendor, [])
        # self-alias(제조사명과 동일한 alias)는 표시 목록에서 제외
        display_aliases = [a for a in all_aliases if a["alias_value"] != vendor]
        meta = meta_map.get(vendor, {})
        results.append(
            {
                "vendor": vendor,
                "product_count": vendor_product_map.get(vendor, 0),
                "alias_count": len(display_aliases),
                "aliases": display_aliases,
                "name_ko": meta.get("name_ko"),
                "memo": meta.get("memo"),
                "similar_product_count": vendor_similar_map.get(vendor, 0),
            }
        )
    results.sort(key=lambda r: (r["vendor"] or "").lower())
    return results


def list_attribute_option_aliases(
    db: Session,
    *,
    attribute_key: str | None = None,
    q: str | None = None,
    active_only: bool = False,
) -> list[dict]:
    stmt = (
        select(
            CatalogAttributeOptionAlias,
            CatalogAttributeOption,
            CatalogAttributeDef,
            func.count(ProductCatalogAttributeValue.id).label("mapped_product_count"),
        )
        .join(CatalogAttributeOption, CatalogAttributeOption.id == CatalogAttributeOptionAlias.attribute_option_id)
        .join(CatalogAttributeDef, CatalogAttributeDef.id == CatalogAttributeOption.attribute_id)
        .outerjoin(ProductCatalogAttributeValue, ProductCatalogAttributeValue.option_id == CatalogAttributeOption.id)
        .group_by(CatalogAttributeOptionAlias.id, CatalogAttributeOption.id, CatalogAttributeDef.id)
        .order_by(
            CatalogAttributeDef.sort_order.asc(),
            CatalogAttributeDef.id.asc(),
            CatalogAttributeOption.sort_order.asc(),
            CatalogAttributeOption.id.asc(),
            CatalogAttributeOptionAlias.sort_order.asc(),
            CatalogAttributeOptionAlias.id.asc(),
        )
    )
    if attribute_key:
        stmt = stmt.where(CatalogAttributeDef.attribute_key == attribute_key)
    if active_only:
        stmt = stmt.where(
            CatalogAttributeOptionAlias.is_active.is_(True),
            CatalogAttributeOption.is_active.is_(True),
            CatalogAttributeDef.is_active.is_(True),
        )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            CatalogAttributeOptionAlias.alias_value.ilike(like)
            | CatalogAttributeOption.label.ilike(like)
            | CatalogAttributeDef.label.ilike(like)
        )

    rows = db.execute(stmt).all()
    return [_serialize_attribute_option_alias(alias, option, attribute, int(mapped_product_count or 0)) for alias, option, attribute, mapped_product_count in rows]


def get_attribute_option_alias(db: Session, alias_id: int) -> dict:
    row = _get_attribute_option_alias_row(db, alias_id)
    if row is None:
        raise NotFoundError("속성 alias를 찾을 수 없습니다.")
    alias, option, attribute, mapped_product_count = row
    return _serialize_attribute_option_alias(alias, option, attribute, int(mapped_product_count or 0))


def create_attribute_option_alias(
    db: Session,
    payload: CatalogAttributeOptionAliasCreate,
    current_user: User,
) -> dict:
    _require_taxonomy_edit(current_user)
    option = _resolve_alias_target_option(db, payload.attribute_key, payload.option_id, payload.option_key)
    normalized_alias = normalize_catalog_alias(payload.alias_value)
    if not normalized_alias:
        raise BusinessRuleError("alias 값이 비어 있습니다.")
    _ensure_attribute_option_alias_unique(db, option.id, normalized_alias)
    alias = CatalogAttributeOptionAlias(
        attribute_option_id=option.id,
        alias_value=payload.alias_value.strip(),
        normalized_alias=normalized_alias,
        match_type=payload.match_type,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(alias)
    db.commit()
    return get_attribute_option_alias(db, alias.id)


def update_attribute_option_alias(
    db: Session,
    alias_id: int,
    payload: CatalogAttributeOptionAliasUpdate,
    current_user: User,
) -> dict:
    _require_taxonomy_edit(current_user)
    alias = db.get(CatalogAttributeOptionAlias, alias_id)
    if alias is None:
        raise NotFoundError("속성 alias를 찾을 수 없습니다.")
    option = alias.attribute_option
    updates = payload.model_dump(exclude_unset=True)
    if "option_id" in updates or "option_key" in updates:
        target_attribute_key = updates.get("attribute_key") or option.attribute.attribute_key
        option = _resolve_alias_target_option(db, target_attribute_key, updates.get("option_id"), updates.get("option_key"))
        alias.attribute_option_id = option.id
    if "alias_value" in updates:
        alias.alias_value = updates["alias_value"].strip()
        alias.normalized_alias = normalize_catalog_alias(alias.alias_value)
    if not alias.normalized_alias:
        raise BusinessRuleError("alias 값이 비어 있습니다.")
    if "match_type" in updates:
        alias.match_type = updates["match_type"]
    if "sort_order" in updates:
        alias.sort_order = updates["sort_order"]
    if "is_active" in updates:
        alias.is_active = updates["is_active"]
    _ensure_attribute_option_alias_unique(db, alias.attribute_option_id, alias.normalized_alias, exclude_alias_id=alias.id)
    db.commit()
    return get_attribute_option_alias(db, alias.id)


def delete_attribute_option_alias(db: Session, alias_id: int, current_user: User) -> None:
    _require_taxonomy_edit(current_user)
    alias = db.get(CatalogAttributeOptionAlias, alias_id)
    if alias is None:
        raise NotFoundError("속성 alias를 찾을 수 없습니다.")
    db.delete(alias)
    db.commit()


def bulk_upsert_vendor_aliases(
    db: Session,
    rows: list[CatalogVendorBulkUpsertRow],
    current_user: User,
) -> dict:
    from app.modules.infra.models.product_catalog import ProductCatalog

    _require_taxonomy_edit(current_user)
    results: list[dict] = []
    updated = 0
    failed = 0

    for index, row in enumerate(rows, start=1):
        try:
            canonical_vendor = (row.canonical_vendor or "").strip()
            if not canonical_vendor:
                raise BusinessRuleError("대표 제조사명이 비어 있습니다.")
            source_vendor = (row.source_vendor or "").strip() or None
            alias_values = []
            seen_aliases: set[str] = set()
            for value in row.aliases:
                cleaned = (value or "").strip()
                if not cleaned:
                    continue
                normalized = normalize_vendor_name(cleaned)
                if not normalized or normalized in seen_aliases:
                    continue
                seen_aliases.add(normalized)
                alias_values.append((cleaned, normalized))

            if source_vendor and source_vendor != canonical_vendor and row.apply_to_products:
                db.execute(
                    update(ProductCatalog)
                    .where(ProductCatalog.vendor == source_vendor)
                    .values(vendor=canonical_vendor)
                )
            if source_vendor and source_vendor != canonical_vendor:
                db.execute(
                    update(CatalogVendorAlias)
                    .where(CatalogVendorAlias.vendor_canonical == source_vendor)
                    .values(vendor_canonical=canonical_vendor)
                )

            # 기존 alias 중 제출 목록에 없는 것 제거
            existing_aliases = db.scalars(
                select(CatalogVendorAlias).where(
                    CatalogVendorAlias.vendor_canonical == canonical_vendor,
                )
            ).all()
            for ea in existing_aliases:
                if ea.normalized_alias not in seen_aliases:
                    db.delete(ea)

            for alias_value, normalized_alias in alias_values:
                existing = db.scalar(
                    select(CatalogVendorAlias).where(
                        CatalogVendorAlias.vendor_canonical == canonical_vendor,
                        CatalogVendorAlias.normalized_alias == normalized_alias,
                    )
                )
                if existing is None:
                    db.add(
                        CatalogVendorAlias(
                            vendor_canonical=canonical_vendor,
                            alias_value=alias_value,
                            normalized_alias=normalized_alias,
                            sort_order=100,
                            is_active=row.is_active,
                        )
                    )
                else:
                    existing.alias_value = alias_value
                    existing.is_active = row.is_active

            # alias가 하나도 없으면 자기 자신을 alias로 등록 (목록 노출 보장)
            has_any = db.scalar(
                select(CatalogVendorAlias.id).where(
                    CatalogVendorAlias.vendor_canonical == canonical_vendor,
                ).limit(1)
            )
            if not has_any:
                self_normalized = normalize_vendor_name(canonical_vendor)
                if self_normalized:
                    db.add(
                        CatalogVendorAlias(
                            vendor_canonical=canonical_vendor,
                            alias_value=canonical_vendor,
                            normalized_alias=self_normalized,
                            sort_order=0,
                            is_active=True,
                        )
                    )

            # 메타 정보 (한글명, 메모) upsert
            meta = db.get(CatalogVendorMeta, canonical_vendor)
            if meta is None:
                meta = CatalogVendorMeta(vendor_canonical=canonical_vendor)
                db.add(meta)
            if row.name_ko is not None:
                meta.name_ko = row.name_ko.strip() or None
            if row.memo is not None:
                meta.memo = row.memo.strip() or None

            db.commit()
            updated += 1
            results.append(
                {
                    "row_no": index,
                    "canonical_vendor": canonical_vendor,
                    "status": "ok",
                    "action": "updated" if source_vendor else "upserted",
                    "message": None,
                }
            )
        except Exception as exc:
            db.rollback()
            failed += 1
            results.append(
                {
                    "row_no": index,
                    "canonical_vendor": (row.canonical_vendor or "").strip(),
                    "status": "error",
                    "action": "failed",
                    "message": str(exc),
                }
            )

    return {
        "total": len(rows),
        "updated": updated,
        "failed": failed,
        "rows": results,
    }


def delete_vendor_and_aliases(db: Session, vendor_canonical: str, current_user: User) -> None:
    from app.modules.infra.models.product_catalog import ProductCatalog

    _require_taxonomy_edit(current_user)
    canonical = vendor_canonical.strip()
    if not canonical:
        raise BusinessRuleError("제조사명이 비어 있습니다.")

    product_count = db.scalar(
        select(func.count(ProductCatalog.id)).where(ProductCatalog.vendor == canonical)
    ) or 0
    if product_count > 0:
        raise BusinessRuleError(
            f"연결된 제품 {product_count}개가 있어 삭제할 수 없습니다.",
            status_code=409,
        )

    db.query(CatalogVendorAlias).filter(
        CatalogVendorAlias.vendor_canonical == canonical
    ).delete(synchronize_session="fetch")
    # 메타 정보도 함께 삭제
    meta = db.get(CatalogVendorMeta, canonical)
    if meta:
        db.delete(meta)
    db.commit()


def _resolve_alias_target_option(
    db: Session,
    attribute_key: str,
    option_id: int | None,
    option_key: str | None,
) -> CatalogAttributeOption:
    attribute = db.scalar(
        select(CatalogAttributeDef).where(CatalogAttributeDef.attribute_key == attribute_key)
    )
    if attribute is None:
        raise NotFoundError("속성을 찾을 수 없습니다.")
    if option_id is not None:
        option = db.get(CatalogAttributeOption, option_id)
        if option is None or option.attribute_id != attribute.id:
            raise NotFoundError("속성값을 찾을 수 없습니다.")
        return option
    if option_key:
        option = db.scalar(
            select(CatalogAttributeOption).where(
                CatalogAttributeOption.attribute_id == attribute.id,
                CatalogAttributeOption.option_key == option_key,
            )
        )
        if option is not None:
            return option
    raise NotFoundError("대상 속성값을 찾을 수 없습니다.")


def _ensure_attribute_option_alias_unique(
    db: Session,
    option_id: int,
    normalized_alias: str,
    *,
    exclude_alias_id: int | None = None,
) -> None:
    stmt = select(CatalogAttributeOptionAlias).where(
        CatalogAttributeOptionAlias.attribute_option_id == option_id,
        CatalogAttributeOptionAlias.normalized_alias == normalized_alias,
    )
    if exclude_alias_id is not None:
        stmt = stmt.where(CatalogAttributeOptionAlias.id != exclude_alias_id)
    if db.scalar(stmt) is not None:
        raise DuplicateError("같은 속성값에 이미 등록된 alias입니다.")


def _get_attribute_option_alias_row(db: Session, alias_id: int):
    return db.execute(
        select(
            CatalogAttributeOptionAlias,
            CatalogAttributeOption,
            CatalogAttributeDef,
            func.count(ProductCatalogAttributeValue.id).label("mapped_product_count"),
        )
        .join(CatalogAttributeOption, CatalogAttributeOption.id == CatalogAttributeOptionAlias.attribute_option_id)
        .join(CatalogAttributeDef, CatalogAttributeDef.id == CatalogAttributeOption.attribute_id)
        .outerjoin(ProductCatalogAttributeValue, ProductCatalogAttributeValue.option_id == CatalogAttributeOption.id)
        .where(CatalogAttributeOptionAlias.id == alias_id)
        .group_by(CatalogAttributeOptionAlias.id, CatalogAttributeOption.id, CatalogAttributeDef.id)
    ).first()


def _serialize_attribute_option_alias(
    alias: CatalogAttributeOptionAlias,
    option: CatalogAttributeOption,
    attribute: CatalogAttributeDef,
    mapped_product_count: int,
) -> dict:
    return {
        "id": alias.id,
        "attribute_option_id": alias.attribute_option_id,
        "alias_value": alias.alias_value,
        "normalized_alias": alias.normalized_alias,
        "match_type": alias.match_type,
        "sort_order": alias.sort_order,
        "is_active": alias.is_active,
        "attribute_id": attribute.id,
        "attribute_key": attribute.attribute_key,
        "attribute_label": attribute.label,
        "option_id": option.id,
        "option_key": option.option_key,
        "option_label": option.label,
        "mapped_product_count": mapped_product_count,
    }


def _require_taxonomy_edit(current_user: User) -> None:
    if not can_manage_catalog_taxonomy(current_user):
        raise PermissionDeniedError("카탈로그 기준 관리 권한이 필요합니다.")

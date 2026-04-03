# app/modules/infra/services/catalog_merge_service.py
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.product_similarity_dismissal import ProductSimilarityDismissal
from app.modules.infra.services.product_catalog_service import invalidate_product_list_cache


def merge_products(
    db: Session,
    *,
    source_id: int,
    target_id: int,
    current_user: User,
) -> dict:
    if source_id == target_id:
        raise BusinessRuleError("동일한 제품을 병합할 수 없습니다.")

    source = db.get(ProductCatalog, source_id)
    target = db.get(ProductCatalog, target_id)
    if not source:
        raise BusinessRuleError("원본 제품을 찾을 수 없습니다.", status_code=404)
    if not target:
        raise BusinessRuleError("대상 제품을 찾을 수 없습니다.", status_code=404)
    if source.is_placeholder:
        raise BusinessRuleError("시스템 placeholder 항목은 병합할 수 없습니다.")

    # 자산 이전
    asset_count = db.scalar(
        select(func.count()).select_from(Asset).where(Asset.model_id == source_id)
    ) or 0

    if asset_count > 0:
        db.execute(
            update(Asset).where(Asset.model_id == source_id).values(model_id=target_id)
        )

    result = {
        "merged_asset_count": asset_count,
        "source_vendor": source.vendor,
        "source_name": source.name,
        "target_vendor": target.vendor,
        "target_name": target.name,
    }

    audit.log(
        db,
        user_id=current_user.id,
        action="merge",
        entity_type="product_catalog",
        entity_id=target.id,
        summary=f"제품 병합: {source.vendor} {source.name} → {target.vendor} {target.name} (자산 {asset_count}건 이전)",
        module="infra",
    )

    # source 삭제 (CASCADE: specs, interfaces, attributes, cache)
    db.delete(source)
    db.commit()
    invalidate_product_list_cache(db)

    return result


def dismiss_similarity(
    db: Session,
    *,
    product_id_a: int,
    product_id_b: int,
) -> None:
    # a < b로 정규화
    a, b = min(product_id_a, product_id_b), max(product_id_a, product_id_b)

    existing = db.scalar(
        select(ProductSimilarityDismissal).where(
            ProductSimilarityDismissal.product_id_a == a,
            ProductSimilarityDismissal.product_id_b == b,
        )
    )
    if existing:
        return

    db.add(ProductSimilarityDismissal(product_id_a=a, product_id_b=b))
    db.commit()


def get_dismissed_pairs(db: Session, product_id: int) -> set[int]:
    """주어진 product_id와 무시 관계에 있는 상대 product_id 집합을 반환."""
    rows = db.execute(
        select(
            ProductSimilarityDismissal.product_id_a,
            ProductSimilarityDismissal.product_id_b,
        ).where(
            (ProductSimilarityDismissal.product_id_a == product_id)
            | (ProductSimilarityDismissal.product_id_b == product_id)
        )
    ).all()
    result: set[int] = set()
    for a, b in rows:
        result.add(a if a != product_id else b)
    return result

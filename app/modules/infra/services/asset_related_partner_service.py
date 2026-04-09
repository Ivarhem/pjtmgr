from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.models.partner import Partner
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_related_partner import AssetRelatedPartner
from app.modules.infra.services.asset_event_service import log_asset_event


def list_asset_related_partners(db: Session, asset_id: int) -> list[dict]:
    _ensure_asset_exists(db, asset_id)
    rows = list(
        db.execute(
            select(
                AssetRelatedPartner,
                Partner.name,
                Partner.partner_type,
                Partner.phone,
            )
            .join(Partner, Partner.id == AssetRelatedPartner.partner_id)
            .where(AssetRelatedPartner.asset_id == asset_id)
            .order_by(
                AssetRelatedPartner.is_primary.desc(),
                AssetRelatedPartner.relation_type.asc(),
                Partner.name.asc(),
                AssetRelatedPartner.id.asc(),
            )
        )
    )
    result = []
    for rel, partner_name, partner_type, partner_phone in rows:
        result.append(
            {
                "id": rel.id,
                "asset_id": rel.asset_id,
                "partner_id": rel.partner_id,
                "partner_name": partner_name,
                "partner_type": partner_type,
                "partner_phone": partner_phone,
                "relation_type": rel.relation_type,
                "is_primary": rel.is_primary,
                "valid_from": rel.valid_from,
                "valid_to": rel.valid_to,
                "note": rel.note,
                "created_at": rel.created_at,
                "updated_at": rel.updated_at,
            }
        )
    return result


def get_asset_related_partner(db: Session, asset_related_partner_id: int) -> AssetRelatedPartner:
    rel = db.get(AssetRelatedPartner, asset_related_partner_id)
    if rel is None:
        raise NotFoundError("Asset related partner not found")
    return rel


def create_asset_related_partner(
    db: Session,
    payload: AssetRelatedPartnerCreate,
    current_user,
) -> AssetRelatedPartner:
    _require_inventory_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)
    _ensure_partner_exists(db, payload.partner_id)
    _ensure_valid_range(payload.valid_from, payload.valid_to)
    _ensure_active_relation_unique(
        db,
        asset_id=payload.asset_id,
        partner_id=payload.partner_id,
        relation_type=payload.relation_type,
        is_open_ended=payload.valid_to is None,
    )
    if payload.is_primary:
        _clear_primary_relation(db, payload.asset_id, payload.relation_type)

    rel = AssetRelatedPartner(**payload.model_dump())
    db.add(rel)
    asset = db.get(Asset, payload.asset_id)
    partner = db.get(Partner, payload.partner_id)
    if asset is not None and partner is not None:
        log_asset_event(
            db,
            asset=asset,
            event_type="maintenance_change" if payload.relation_type == "maintainer" else "note",
            summary=_build_summary("create", partner.name, payload.relation_type),
            detail=_build_detail("create", partner.name, payload.relation_type, payload.note),
            created_by_user_id=getattr(current_user, "id", None),
        )
    db.commit()
    db.refresh(rel)
    return rel


def update_asset_related_partner(
    db: Session,
    asset_related_partner_id: int,
    payload: AssetRelatedPartnerUpdate,
    current_user,
) -> AssetRelatedPartner:
    _require_inventory_edit(current_user)
    rel = get_asset_related_partner(db, asset_related_partner_id)
    changes = payload.model_dump(exclude_unset=True)
    target_relation_type = changes.get("relation_type", rel.relation_type)
    target_valid_from = changes.get("valid_from", rel.valid_from)
    target_valid_to = changes.get("valid_to", rel.valid_to)
    _ensure_valid_range(target_valid_from, target_valid_to)
    if (
        target_relation_type != rel.relation_type
        or target_valid_to != rel.valid_to
    ):
        _ensure_active_relation_unique(
            db,
            asset_id=rel.asset_id,
            partner_id=rel.partner_id,
            relation_type=target_relation_type,
            is_open_ended=target_valid_to is None,
            asset_related_partner_id=rel.id,
        )
    if changes.get("is_primary") is True:
        _clear_primary_relation(db, rel.asset_id, target_relation_type, rel.id)

    for field, value in changes.items():
        setattr(rel, field, value)

    asset = db.get(Asset, rel.asset_id)
    partner = db.get(Partner, rel.partner_id)
    if asset is not None and partner is not None and changes:
        log_asset_event(
            db,
            asset=asset,
            event_type="maintenance_change" if target_relation_type == "maintainer" else "note",
            summary=_build_summary("update", partner.name, target_relation_type),
            detail=_build_detail(
                "update",
                partner.name,
                target_relation_type,
                "변경 필드: " + ", ".join(sorted(changes.keys())),
            ),
            created_by_user_id=getattr(current_user, "id", None),
        )
    db.commit()
    db.refresh(rel)
    return rel


def delete_asset_related_partner(
    db: Session,
    asset_related_partner_id: int,
    current_user,
) -> None:
    _require_inventory_edit(current_user)
    rel = get_asset_related_partner(db, asset_related_partner_id)
    asset = db.get(Asset, rel.asset_id)
    partner = db.get(Partner, rel.partner_id)
    if asset is not None and partner is not None:
        log_asset_event(
            db,
            asset=asset,
            event_type="maintenance_change" if rel.relation_type == "maintainer" else "note",
            summary=_build_summary("delete", partner.name, rel.relation_type),
            detail=_build_detail("delete", partner.name, rel.relation_type, rel.note),
            created_by_user_id=getattr(current_user, "id", None),
        )
    db.delete(rel)
    db.commit()


def delete_asset_related_partners_for_asset(db: Session, asset_id: int) -> None:
    rows = list(
        db.scalars(select(AssetRelatedPartner).where(AssetRelatedPartner.asset_id == asset_id))
    )
    for row in rows:
        db.delete(row)


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _ensure_partner_exists(db: Session, partner_id: int) -> None:
    if db.get(Partner, partner_id) is None:
        raise NotFoundError("Partner not found")


def _ensure_valid_range(valid_from, valid_to) -> None:
    if valid_from is not None and valid_to is not None and valid_from > valid_to:
        raise BusinessRuleError("유효 시작일은 종료일보다 늦을 수 없습니다.", status_code=422)


def _ensure_active_relation_unique(
    db: Session,
    asset_id: int,
    partner_id: int,
    relation_type: str,
    is_open_ended: bool,
    asset_related_partner_id: int | None = None,
) -> None:
    if not is_open_ended:
        return
    stmt = select(AssetRelatedPartner).where(
        AssetRelatedPartner.asset_id == asset_id,
        AssetRelatedPartner.partner_id == partner_id,
        AssetRelatedPartner.relation_type == relation_type,
        AssetRelatedPartner.valid_to.is_(None),
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_related_partner_id is not None and existing.id == asset_related_partner_id:
        return
    raise DuplicateError("같은 업체/관계유형의 활성 연결이 이미 존재합니다.")


def _clear_primary_relation(
    db: Session,
    asset_id: int,
    relation_type: str,
    exclude_id: int | None = None,
) -> None:
    stmt = select(AssetRelatedPartner).where(
        AssetRelatedPartner.asset_id == asset_id,
        AssetRelatedPartner.relation_type == relation_type,
        AssetRelatedPartner.is_primary.is_(True),
    )
    rows = list(db.scalars(stmt))
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue
        row.is_primary = False


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")


def _build_summary(action: str, partner_name: str, relation_type: str) -> str:
    label = _relation_label(relation_type)
    if action == "create":
        return f"{label} 연결: {partner_name}"
    if action == "update":
        return f"{label} 변경: {partner_name}"
    return f"{label} 해제: {partner_name}"


def _build_detail(action: str, partner_name: str, relation_type: str, note: str | None) -> str:
    prefix = {
        "create": "관련업체가 연결되었습니다.",
        "update": "관련업체 정보가 변경되었습니다.",
        "delete": "관련업체 연결이 해제되었습니다.",
    }[action]
    parts = [prefix, f"업체: {partner_name}", f"관계: {_relation_label(relation_type)}"]
    if note:
        parts.append(f"메모: {note}")
    return "\n".join(parts)


def _relation_label(relation_type: str) -> str:
    return {
        "maintainer": "유지보수사",
        "supplier": "공급사",
        "installer": "설치사",
        "operator": "운영사",
        "carrier": "통신사",
        "vendor": "제조사/벤더",
        "lessor": "임대사",
        "owner": "소유주체",
        "other": "기타업체",
    }.get(relation_type, relation_type)

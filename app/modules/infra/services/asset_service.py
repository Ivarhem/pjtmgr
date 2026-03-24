from __future__ import annotations

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_contact import AssetContact
from app.modules.infra.schemas.asset import AssetCreate, AssetUpdate
from app.modules.infra.services._helpers import ensure_partner_exists, get_period_asset_ids
from app.modules.infra.schemas.asset_contact import (
    AssetContactCreate,
    AssetContactUpdate,
)
from app.modules.common.models.partner_contact import PartnerContact


# ── Asset ──


def list_assets(
    db: Session,
    partner_id: int,
    period_id: int | None = None,
    asset_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
) -> list[Asset]:
    stmt = select(Asset).where(Asset.partner_id == partner_id)
    if period_id is not None:
        asset_ids = get_period_asset_ids(db, period_id)
        if not asset_ids:
            return []
        stmt = stmt.where(Asset.id.in_(asset_ids))
    if asset_type is not None:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if status is not None:
        stmt = stmt.where(Asset.status == status)
    if q:
        from app.modules.infra.models.asset_alias import AssetAlias
        like = f"%{q}%"
        alias_exists = exists(
            select(AssetAlias.id).where(
                AssetAlias.asset_id == Asset.id,
                AssetAlias.alias_name.ilike(like),
            )
        )
        stmt = stmt.where(
            Asset.asset_name.ilike(like)
            | Asset.hostname.ilike(like)
            | Asset.service_ip.ilike(like)
            | Asset.equipment_id.ilike(like)
            | Asset.asset_code.ilike(like)
            | alias_exists
        )
    stmt = stmt.order_by(Asset.asset_name.asc())
    return list(db.scalars(stmt))


def enrich_assets_with_period(db: Session, assets: list[Asset]) -> list[dict]:
    """Attach period_label via PeriodAsset for inventory view."""
    from app.modules.common.models.contract_period import ContractPeriod
    from app.modules.infra.models.period_asset import PeriodAsset

    if not assets:
        return []

    asset_ids = [a.id for a in assets]
    # Load PeriodAsset links for these assets
    pa_rows = list(
        db.execute(
            select(PeriodAsset.asset_id, PeriodAsset.contract_period_id).where(
                PeriodAsset.asset_id.in_(asset_ids)
            )
        )
    )
    # Map asset_id -> first contract_period_id (for display)
    asset_period_map: dict[int, int] = {}
    period_ids: set[int] = set()
    for row in pa_rows:
        if row.asset_id not in asset_period_map:
            asset_period_map[row.asset_id] = row.contract_period_id
        period_ids.add(row.contract_period_id)

    periods = {}
    if period_ids:
        periods = {
            p.id: p
            for p in db.scalars(select(ContractPeriod).where(ContractPeriod.id.in_(period_ids)))
        }

    result = []
    for a in assets:
        d = {c.key: getattr(a, c.key) for c in Asset.__table__.columns}
        d["created_at"] = a.created_at
        d["updated_at"] = a.updated_at
        period_id = asset_period_map.get(a.id)
        period = periods.get(period_id) if period_id else None
        d["period_label"] = period.period_label if period else None
        result.append(d)
    return result


def get_asset(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def create_asset(db: Session, payload: AssetCreate, current_user) -> Asset:
    from sqlalchemy.exc import IntegrityError
    from app.modules.common.services.asset_type_code import get_valid_type_keys

    _require_inventory_edit(current_user)
    ensure_partner_exists(db, payload.partner_id)
    _ensure_asset_name_unique(db, payload.partner_id, payload.asset_name)

    # 유형 검증
    valid_keys = get_valid_type_keys(db)
    if payload.asset_type not in valid_keys:
        raise NotFoundError(f"유효하지 않은 자산유형: {payload.asset_type}")

    if payload.hardware_model_id is not None:
        _ensure_hardware_model_exists(db, payload.hardware_model_id)

    data = payload.model_dump()
    data.pop("asset_code", None)  # 사용자 입력 무시

    # 코드 자동 생성 (동시성 충돌 시 최대 3회 재시도)
    for attempt in range(3):
        data["asset_code"] = _generate_asset_code(db, payload.partner_id, payload.asset_type)
        asset = Asset(**data)
        db.add(asset)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise

    audit.log(
        db, user_id=current_user.id, action="create", entity_type="asset",
        entity_id=None, summary=f"자산 생성: {asset.asset_name}", module="infra",
    )
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(
    db: Session, asset_id: int, payload: AssetUpdate, current_user
) -> Asset:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    changes = payload.model_dump(exclude_unset=True)

    if "asset_type" in changes and changes["asset_type"] != asset.asset_type:
        raise PermissionDeniedError("자산 유형은 변경할 수 없습니다.")
    changes.pop("asset_type", None)
    changes.pop("asset_code", None)  # 코드 수동 변경 차단

    target_partner_id = changes.get("partner_id", asset.partner_id)
    target_asset_name = changes.get("asset_name", asset.asset_name)

    if "partner_id" in changes:
        ensure_partner_exists(db, target_partner_id)

    if target_partner_id != asset.partner_id or target_asset_name != asset.asset_name:
        _ensure_asset_name_unique(db, target_partner_id, target_asset_name, asset.id)

    if "hardware_model_id" in changes and changes["hardware_model_id"] is not None:
        _ensure_hardware_model_exists(db, changes["hardware_model_id"])

    for field, value in changes.items():
        setattr(asset, field, value)

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="asset",
        entity_id=asset.id, summary=f"자산 수정: {asset.asset_name}", module="infra",
    )
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="asset",
        entity_id=asset.id, summary=f"자산 삭제: {asset.asset_name}", module="infra",
    )
    db.delete(asset)
    db.commit()


# ── AssetContact ──


def list_asset_contacts(db: Session, asset_id: int) -> list[AssetContact]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetContact)
            .where(AssetContact.asset_id == asset_id)
            .order_by(AssetContact.id.asc())
        )
    )


def get_asset_contact(db: Session, asset_contact_id: int) -> AssetContact:
    ac = db.get(AssetContact, asset_contact_id)
    if ac is None:
        raise NotFoundError("Asset contact not found")
    return ac


def create_asset_contact(
    db: Session, payload: AssetContactCreate, current_user
) -> AssetContact:
    _require_inventory_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)
    _ensure_contact_exists(db, payload.contact_id)
    _ensure_asset_contact_unique(db, payload.asset_id, payload.contact_id, payload.role)

    ac = AssetContact(**payload.model_dump())
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def update_asset_contact(
    db: Session, asset_contact_id: int, payload: AssetContactUpdate, current_user
) -> AssetContact:
    _require_inventory_edit(current_user)
    ac = get_asset_contact(db, asset_contact_id)
    changes = payload.model_dump(exclude_unset=True)

    if "role" in changes:
        _ensure_asset_contact_unique(
            db, ac.asset_id, ac.contact_id, changes["role"], asset_contact_id
        )

    for field, value in changes.items():
        setattr(ac, field, value)

    db.commit()
    db.refresh(ac)
    return ac


def delete_asset_contact(db: Session, asset_contact_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    ac = get_asset_contact(db, asset_contact_id)
    db.delete(ac)
    db.commit()


# ── Private helpers ──


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _ensure_hardware_model_exists(db: Session, product_id: int) -> None:
    from app.modules.infra.models.product_catalog import ProductCatalog
    if db.get(ProductCatalog, product_id) is None:
        raise NotFoundError("Product catalog entry not found")


def _ensure_contact_exists(db: Session, contact_id: int) -> None:
    if db.get(PartnerContact, contact_id) is None:
        raise NotFoundError("Contact not found")


def _ensure_asset_name_unique(
    db: Session,
    partner_id: int,
    asset_name: str,
    asset_id: int | None = None,
) -> None:
    stmt = select(Asset).where(
        Asset.partner_id == partner_id, Asset.asset_name == asset_name
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_id is not None and existing.id == asset_id:
        return
    raise DuplicateError("이 고객사에 동일한 자산명이 이미 존재합니다.")


def _ensure_asset_contact_unique(
    db: Session,
    asset_id: int,
    contact_id: int,
    role: str | None,
    asset_contact_id: int | None = None,
) -> None:
    stmt = select(AssetContact).where(
        AssetContact.asset_id == asset_id,
        AssetContact.contact_id == contact_id,
        AssetContact.role == role,
    )
    existing = db.scalar(stmt)
    if existing is None:
        return
    if asset_contact_id is not None and existing.id == asset_contact_id:
        return
    raise DuplicateError("This contact-role mapping already exists for the asset")


_BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _to_base36(num: int, width: int = 4) -> str:
    if num == 0:
        return "0" * width
    result = ""
    while num:
        result = _BASE36_CHARS[num % 36] + result
        num //= 36
    return result.zfill(width)


def _generate_asset_code(db: Session, partner_id: int, type_key: str) -> str:
    """Generate asset code: {partner_code}-{type_code}-{base36 4자리}."""
    from app.modules.common.models.partner import Partner
    from app.modules.common.services.asset_type_code import get_code_for_type_key

    partner = db.get(Partner, partner_id)
    partner_code = partner.partner_code if partner else "X000"
    type_code = get_code_for_type_key(db, type_key)
    prefix = f"{partner_code}-{type_code}-"

    max_code = db.scalar(
        select(func.max(Asset.asset_code))
        .where(Asset.partner_id == partner_id)
        .where(Asset.asset_code.like(f"{prefix}%"))
    )

    if max_code:
        suffix = max_code[len(prefix):]
        next_seq = int(suffix, 36) + 1
    else:
        next_seq = 0

    return prefix + _to_base36(next_seq)


def _require_inventory_edit(current_user) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

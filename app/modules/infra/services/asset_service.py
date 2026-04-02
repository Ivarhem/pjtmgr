from __future__ import annotations

from datetime import date

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_contact import AssetContact
from app.modules.infra.models.center import Center
from app.modules.infra.models.rack import Rack
from app.modules.infra.models.room import Room
from app.modules.infra.models.asset_role import AssetRole
from app.modules.infra.models.asset_role_assignment import AssetRoleAssignment
from app.modules.infra.schemas.asset import AssetCreate, AssetUpdate
from app.modules.infra.services.classification_identity_service import derive_asset_type_identity
from app.modules.infra.services.asset_event_service import log_asset_event
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
    status: str | None = None,
    q: str | None = None,
) -> list[Asset]:
    stmt = select(Asset).where(Asset.partner_id == partner_id)
    if period_id is not None:
        asset_ids = get_period_asset_ids(db, period_id)
        if not asset_ids:
            return []
        stmt = stmt.where(Asset.id.in_(asset_ids))
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
            | Asset.project_asset_number.ilike(like)
            | Asset.customer_asset_number.ilike(like)
            | Asset.hostname.ilike(like)
            | Asset.service_ip.ilike(like)
            | Asset.equipment_id.ilike(like)
            | Asset.asset_code.ilike(like)
            | alias_exists
        )
    stmt = stmt.order_by(Asset.asset_name.asc())
    return list(db.scalars(stmt))


def enrich_assets_with_aliases(db: Session, assets: list[Asset]) -> list[dict]:
    """Attach alias names to each asset for list display."""
    from app.modules.infra.models.asset_alias import AssetAlias
    from app.modules.infra.models.product_catalog import ProductCatalog
    from app.modules.infra.models.asset_role import AssetRole
    from app.modules.infra.models.asset_role_assignment import AssetRoleAssignment

    if not assets:
        return []

    asset_ids = [a.id for a in assets]
    catalog_ids = {a.model_id for a in assets}
    alias_rows = list(db.execute(
        select(AssetAlias.asset_id, AssetAlias.alias_name)
        .where(AssetAlias.asset_id.in_(asset_ids))
        .order_by(AssetAlias.is_primary.desc(), AssetAlias.alias_name)
    ))
    catalog_map = {}
    catalog_entity_map = {}
    if catalog_ids:
        catalog_rows = list(db.scalars(select(ProductCatalog).where(ProductCatalog.id.in_(catalog_ids))))
        catalog_map = {c.id: c.product_type for c in catalog_rows}
        catalog_entity_map = {c.id: c for c in catalog_rows}
    alias_map: dict[int, list[str]] = {}
    for row in alias_rows:
        alias_map.setdefault(row.asset_id, []).append(row.alias_name)
    role_rows = list(
        db.execute(
            select(
                AssetRoleAssignment.asset_id,
                AssetRole.id,
                AssetRole.role_name,
            )
            .join(AssetRole, AssetRole.id == AssetRoleAssignment.asset_role_id)
            .where(
                AssetRoleAssignment.asset_id.in_(asset_ids),
                AssetRoleAssignment.is_current.is_(True),
            )
            .order_by(AssetRoleAssignment.id.desc())
        )
    )
    role_map: dict[int, list[dict]] = {}
    for row in role_rows:
        role_map.setdefault(row.asset_id, []).append({"id": row.id, "name": row.role_name})
    center_ids = {a.center_id for a in assets if a.center_id}
    room_ids = {a.room_id for a in assets if a.room_id}
    rack_ids = {a.rack_id for a in assets if a.rack_id}
    center_map = {
        item.id: item for item in db.scalars(select(Center).where(Center.id.in_(center_ids)))
    } if center_ids else {}
    room_map = {
        item.id: item for item in db.scalars(select(Room).where(Room.id.in_(room_ids)))
    } if room_ids else {}
    rack_map = {
        item.id: item for item in db.scalars(select(Rack).where(Rack.id.in_(rack_ids)))
    } if rack_ids else {}
    result = []
    for asset in assets:
        d = {c.key: getattr(asset, c.key) for c in Asset.__table__.columns}
        d["aliases"] = alias_map.get(asset.id, [])
        d["catalog_kind"] = catalog_map.get(asset.model_id)
        current_roles = role_map.get(asset.id, [])
        d["current_role_names"] = [role["name"] for role in current_roles]
        d["current_role_id"] = current_roles[0]["id"] if current_roles else None
        d["center_label"] = center_map.get(asset.center_id).center_name if asset.center_id in center_map else asset.center
        d["room_label"] = room_map.get(asset.room_id).room_name if asset.room_id in room_map else None
        d["rack_label"] = rack_map.get(asset.rack_id).rack_name or rack_map.get(asset.rack_id).rack_code if asset.rack_id in rack_map else asset.rack_no
        d["center_is_fallback_text"] = bool(not asset.center_id and asset.center)
        d["rack_is_fallback_text"] = bool(not asset.rack_id and asset.rack_no)
        classification_info = _build_classification_info(
            db,
            catalog_entity_map.get(asset.model_id),
            category=asset.category,
            subcategory=asset.subcategory,
        )
        d["classification_path"] = classification_info["path"]
        d["classification_is_fallback_text"] = classification_info["is_fallback_text"]
        d["classification_level_1_name"] = classification_info["levels"][0]
        d["classification_level_2_name"] = classification_info["levels"][1]
        d["classification_level_3_name"] = classification_info["levels"][2]
        d["classification_level_4_name"] = classification_info["levels"][3]
        d["classification_level_5_name"] = classification_info["levels"][4]
        result.append(d)
    return result


def enrich_assets_with_period(
    db: Session,
    assets: list[Asset],
    *,
    layout_id: int | None = None,
    lang: str | None = None,
) -> list[dict]:
    """Attach period_label via PeriodAsset for inventory view."""
    from app.modules.common.models.contract_period import ContractPeriod
    from app.modules.infra.models.period_asset import PeriodAsset
    from app.modules.infra.models.product_catalog import ProductCatalog
    from app.modules.infra.models.asset_role import AssetRole
    from app.modules.infra.models.asset_role_assignment import AssetRoleAssignment

    if not assets:
        return []

    asset_ids = [a.id for a in assets]
    catalog_ids = {a.model_id for a in assets}
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
            for p in db.scalars(
                select(ContractPeriod)
                .options(joinedload(ContractPeriod.contract))
                .where(ContractPeriod.id.in_(period_ids))
            )
        }
    catalog_map = {}
    catalog_entity_map = {}
    if catalog_ids:
        catalog_rows = list(db.scalars(select(ProductCatalog).where(ProductCatalog.id.in_(catalog_ids))))
        catalog_map = {c.id: c.product_type for c in catalog_rows}
        catalog_entity_map = {c.id: c for c in catalog_rows}
    role_rows = list(
        db.execute(
            select(
                AssetRoleAssignment.asset_id,
                AssetRole.id,
                AssetRole.role_name,
            )
            .join(AssetRole, AssetRole.id == AssetRoleAssignment.asset_role_id)
            .where(
                AssetRoleAssignment.asset_id.in_(asset_ids),
                AssetRoleAssignment.is_current.is_(True),
            )
            .order_by(AssetRoleAssignment.id.desc())
        )
    )
    role_map: dict[int, list[dict]] = {}
    for row in role_rows:
        role_map.setdefault(row.asset_id, []).append({"id": row.id, "name": row.role_name})
    center_ids = {a.center_id for a in assets if a.center_id}
    room_ids = {a.room_id for a in assets if a.room_id}
    rack_ids = {a.rack_id for a in assets if a.rack_id}
    center_map = {
        item.id: item for item in db.scalars(select(Center).where(Center.id.in_(center_ids)))
    } if center_ids else {}
    room_map = {
        item.id: item for item in db.scalars(select(Room).where(Room.id.in_(room_ids)))
    } if room_ids else {}
    rack_map = {
        item.id: item for item in db.scalars(select(Rack).where(Rack.id.in_(rack_ids)))
    } if rack_ids else {}
    result = []
    for a in assets:
        d = {c.key: getattr(a, c.key) for c in Asset.__table__.columns}
        d["created_at"] = a.created_at
        d["updated_at"] = a.updated_at
        period_id = asset_period_map.get(a.id)
        period = periods.get(period_id) if period_id else None
        d["period_id"] = period_id
        d["period_label"] = period.period_label if period else None
        d["contract_name"] = period.contract.contract_name if period and period.contract else None
        d["catalog_kind"] = catalog_map.get(a.model_id)
        current_roles = role_map.get(a.id, [])
        d["current_role_names"] = [role["name"] for role in current_roles]
        d["current_role_id"] = current_roles[0]["id"] if current_roles else None
        d["center_label"] = center_map.get(a.center_id).center_name if a.center_id in center_map else a.center
        d["room_label"] = room_map.get(a.room_id).room_name if a.room_id in room_map else None
        d["rack_label"] = rack_map.get(a.rack_id).rack_name or rack_map.get(a.rack_id).rack_code if a.rack_id in rack_map else a.rack_no
        d["center_is_fallback_text"] = bool(not a.center_id and a.center)
        d["rack_is_fallback_text"] = bool(not a.rack_id and a.rack_no)
        classification_info = _build_classification_info(
            db,
            catalog_entity_map.get(a.model_id),
            period_id=period_id,
            category=a.category,
            subcategory=a.subcategory,
            layout_id=layout_id,
            lang=lang,
        )
        d["classification_path"] = classification_info["path"]
        d["classification_is_fallback_text"] = classification_info["is_fallback_text"]
        d["classification_level_1_name"] = classification_info["levels"][0]
        d["classification_level_2_name"] = classification_info["levels"][1]
        d["classification_level_3_name"] = classification_info["levels"][2]
        d["classification_level_4_name"] = classification_info["levels"][3]
        d["classification_level_5_name"] = classification_info["levels"][4]
        result.append(d)
    return result


def enrich_asset_with_catalog_kind(db: Session, asset: Asset) -> dict:
    from app.modules.common.models.contract_period import ContractPeriod
    from app.modules.infra.models.period_asset import PeriodAsset
    from app.modules.infra.models.product_catalog import ProductCatalog
    from app.modules.infra.models.asset_role import AssetRole
    from app.modules.infra.models.asset_role_assignment import AssetRoleAssignment

    d = {c.key: getattr(asset, c.key) for c in Asset.__table__.columns}
    d["created_at"] = asset.created_at
    d["updated_at"] = asset.updated_at
    d["period_id"] = None
    d["period_label"] = None
    d["contract_name"] = None
    d["aliases"] = []
    d["catalog_kind"] = None
    d["current_role_names"] = []
    d["current_role_id"] = None
    catalog = db.get(ProductCatalog, asset.model_id)
    if catalog is not None:
        d["catalog_kind"] = catalog.product_type
    if asset.center_id:
        center = db.get(Center, asset.center_id)
        if center is not None:
            d["center_label"] = center.center_name
    d["center_is_fallback_text"] = bool(not asset.center_id and asset.center)
    if asset.room_id:
        room = db.get(Room, asset.room_id)
        if room is not None:
            d["room_label"] = room.room_name
    if asset.rack_id:
        rack = db.get(Rack, asset.rack_id)
        if rack is not None:
            d["rack_label"] = rack.rack_name or rack.rack_code
    d["rack_is_fallback_text"] = bool(not asset.rack_id and asset.rack_no)
    classification_info = _build_classification_info(
        db,
        catalog,
        period_id=None,
        category=asset.category,
        subcategory=asset.subcategory,
    )
    d["classification_path"] = classification_info["path"]
    d["classification_is_fallback_text"] = classification_info["is_fallback_text"]
    d["classification_level_1_name"] = classification_info["levels"][0]
    d["classification_level_2_name"] = classification_info["levels"][1]
    d["classification_level_3_name"] = classification_info["levels"][2]
    d["classification_level_4_name"] = classification_info["levels"][3]
    d["classification_level_5_name"] = classification_info["levels"][4]
    period_link = db.scalar(
        select(PeriodAsset).where(PeriodAsset.asset_id == asset.id).order_by(PeriodAsset.id.asc())
    )
    if period_link is not None:
        d["period_id"] = period_link.contract_period_id
        period = db.get(ContractPeriod, period_link.contract_period_id)
        if period is not None:
            d["period_label"] = period.period_label
            d["contract_name"] = period.contract.contract_name if period.contract else None
    current_assignments = list(
        db.execute(
            select(AssetRole.id, AssetRole.role_name)
            .join(AssetRoleAssignment, AssetRoleAssignment.asset_role_id == AssetRole.id)
            .where(
                AssetRoleAssignment.asset_id == asset.id,
                AssetRoleAssignment.is_current.is_(True),
            )
            .order_by(AssetRoleAssignment.id.desc())
        )
    )
    if current_assignments:
        d["current_role_names"] = [row.role_name for row in current_assignments]
        d["current_role_id"] = current_assignments[0].id
    return d


def get_asset(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def create_asset(db: Session, payload: AssetCreate, current_user) -> Asset:
    from sqlalchemy.exc import IntegrityError
    from app.modules.infra.models.product_catalog import ProductCatalog
    from app.modules.infra.models.period_asset import PeriodAsset

    _require_inventory_edit(current_user)
    ensure_partner_exists(db, payload.partner_id)
    _ensure_asset_name_unique(db, payload.partner_id, payload.asset_name)
    if payload.period_id is not None:
        _ensure_period_belongs_to_partner(db, payload.period_id, payload.partner_id)
    refs = _resolve_physical_refs(
        db,
        partner_id=payload.partner_id,
        center_id=payload.center_id,
        room_id=payload.room_id,
        rack_id=payload.rack_id,
    )

    # 카탈로그 조회
    catalog = db.get(ProductCatalog, payload.model_id)
    if catalog is None:
        raise NotFoundError("Product catalog entry not found")
    catalog_type_meta = _get_catalog_asset_type_meta(db, catalog, period_id=payload.period_id)
    if catalog_type_meta["asset_type_code"] is None:
        raise BusinessRuleError(
            "카탈로그 분류 기준이 올바르지 않습니다.", status_code=422
        )
    # placeholder면 vendor/model 없음, 아니면 카탈로그 값 사용
    if catalog.is_placeholder:
        vendor = None
        model_name = None
    else:
        vendor = catalog.vendor
        model_name = catalog.name
    classification_info = _build_classification_info(
        db,
        catalog,
        period_id=payload.period_id,
    )

    data = {
        "partner_id": payload.partner_id,
        "model_id": payload.model_id,
        "project_asset_number": payload.project_asset_number,
        "customer_asset_number": payload.customer_asset_number,
        "asset_name": payload.asset_name,
        "vendor": vendor,
        "model": model_name,
        "category": _get_deepest_classification_label(classification_info["levels"]),
        "hostname": payload.hostname,
        "center_id": refs["center_id"],
        "room_id": refs["room_id"],
        "rack_id": refs["rack_id"],
        "center": refs["center_code"],
        "rack_no": refs["rack_code"],
        "status": "planned",
        "environment": "prod",
    }

    # 코드 자동 생성 (동시성 충돌 시 최대 3회 재시도)
    for attempt in range(3):
        data["asset_code"] = _generate_asset_code(
            db, payload.partner_id, catalog_type_meta["asset_type_code"]
        )
        asset = Asset(**data)
        db.add(asset)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise

    # 귀속사업 연결
    if payload.period_id is not None:
        pa = PeriodAsset(
            contract_period_id=payload.period_id,
            asset_id=asset.id,
        )
        db.add(pa)

    audit.log(
        db, user_id=current_user.id, action="create", entity_type="asset",
        entity_id=None, summary=f"자산 생성: {asset.asset_name}", module="infra",
    )
    log_asset_event(
        db,
        asset=asset,
        event_type="create",
        summary="자산이 등록되었습니다.",
        detail=f"카탈로그 #{payload.model_id} 기반으로 자산이 생성되었습니다.",
        created_by_user_id=current_user.id,
    )
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(
    db: Session, asset_id: int, payload: AssetUpdate, current_user
) -> Asset:
    from app.modules.infra.models.product_catalog import ProductCatalog
    from app.modules.infra.models.period_asset import PeriodAsset

    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    changes = payload.model_dump(exclude_unset=True)
    period_id = changes.pop("period_id", None) if "period_id" in changes else None
    has_period_change = "period_id" in payload.model_fields_set

    changes.pop("asset_code", None)  # 코드 수동 변경 차단

    target_partner_id = changes.get("partner_id", asset.partner_id)
    target_asset_name = changes.get("asset_name", asset.asset_name)

    if "partner_id" in changes:
        ensure_partner_exists(db, target_partner_id)

    if has_period_change and period_id is not None:
        _ensure_period_belongs_to_partner(db, period_id, target_partner_id)
    if target_partner_id != asset.partner_id or target_asset_name != asset.asset_name:
        _ensure_asset_name_unique(db, target_partner_id, target_asset_name, asset.id)

    if "model_id" in changes and changes["model_id"] is not None:
        new_catalog = db.get(ProductCatalog, changes["model_id"])
        if new_catalog is None:
            raise NotFoundError("Product catalog entry not found")
        period_id_for_layout = (
            period_id
            if has_period_change
            else _current_asset_period_id(db, asset.id)
        )
        new_catalog_type_meta = _get_catalog_asset_type_meta(
            db,
            new_catalog,
            period_id=period_id_for_layout,
        )
        if new_catalog.is_placeholder:
            changes["vendor"] = None
            changes["model"] = None
        else:
            changes["vendor"] = new_catalog.vendor
            changes["model"] = new_catalog.name
        classification_info = _build_classification_info(
            db,
            new_catalog,
            period_id=period_id_for_layout,
        )
        changes["category"] = _get_deepest_classification_label(
            classification_info["levels"]
        )

    if (
        "center_id" in changes
        or "room_id" in changes
        or "rack_id" in changes
        or "partner_id" in changes
    ):
        refs = _resolve_physical_refs(
            db,
            partner_id=target_partner_id,
            center_id=changes.get("center_id", asset.center_id),
            room_id=changes.get("room_id", asset.room_id),
            rack_id=changes.get("rack_id", asset.rack_id),
        )
        changes["center_id"] = refs["center_id"]
        changes["room_id"] = refs["room_id"]
        changes["rack_id"] = refs["rack_id"]
        changes["center"] = refs["center_code"]
        changes["rack_no"] = refs["rack_code"]

    for field, value in changes.items():
        setattr(asset, field, value)

    should_sync_period = has_period_change or target_partner_id != asset.partner_id
    if should_sync_period:
        period_link = db.scalar(
            select(PeriodAsset).where(PeriodAsset.asset_id == asset.id).order_by(PeriodAsset.id.asc())
        )
        if period_link is not None:
            db.delete(period_link)
        if has_period_change and period_id is not None:
            db.add(PeriodAsset(contract_period_id=period_id, asset_id=asset.id))

    changed_fields = sorted(changes.keys())
    if has_period_change:
        changed_fields.append("period_id")

    audit.log(
        db, user_id=current_user.id, action="update", entity_type="asset",
        entity_id=asset.id, summary=f"자산 수정: {asset.asset_name}", module="infra",
    )
    if changed_fields:
        log_asset_event(
            db,
            asset=asset,
            event_type="update",
            summary="자산 정보가 수정되었습니다.",
            detail="변경 필드: " + ", ".join(changed_fields),
            created_by_user_id=current_user.id,
        )
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int, current_user) -> None:
    from app.modules.infra.models.period_asset import PeriodAsset
    from app.modules.infra.services.asset_related_partner_service import (
        delete_asset_related_partners_for_asset,
    )

    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    period_links = list(
        db.scalars(select(PeriodAsset).where(PeriodAsset.asset_id == asset.id))
    )
    for link in period_links:
        db.delete(link)
    delete_asset_related_partners_for_asset(db, asset.id)
    audit.log(
        db, user_id=current_user.id, action="delete", entity_type="asset",
        entity_id=asset.id, summary=f"자산 삭제: {asset.asset_name}", module="infra",
    )
    log_asset_event(
        db,
        asset=asset,
        event_type="delete",
        summary="자산이 삭제되었습니다.",
        detail="자산 원장에서 삭제 처리되었습니다.",
        created_by_user_id=current_user.id,
    )
    db.delete(asset)
    db.commit()


def update_asset_current_role(
    db: Session,
    asset_id: int,
    asset_role_id: int | None,
    current_user,
) -> Asset:
    _require_inventory_edit(current_user)
    asset = get_asset(db, asset_id)
    today = date.today()

    current_assignments = list(
        db.scalars(
            select(AssetRoleAssignment).where(
                AssetRoleAssignment.asset_id == asset.id,
                AssetRoleAssignment.is_current.is_(True),
            )
        )
    )
    previous_role_names = []
    for assignment in current_assignments:
        role = db.get(AssetRole, assignment.asset_role_id)
        if role is not None:
            previous_role_names.append(role.role_name)
        assignment.is_current = False
        if assignment.valid_to is None:
            assignment.valid_to = today

    target_role = None
    if asset_role_id is not None:
        target_role = db.get(AssetRole, asset_role_id)
        if target_role is None:
            raise NotFoundError("Asset role not found")
        if target_role.partner_id != asset.partner_id:
            raise BusinessRuleError("역할과 자산의 고객사가 일치하지 않습니다.", status_code=422)

        role_current_assignments = list(
            db.scalars(
                select(AssetRoleAssignment).where(
                    AssetRoleAssignment.asset_role_id == target_role.id,
                    AssetRoleAssignment.is_current.is_(True),
                )
            )
        )
        for assignment in role_current_assignments:
            assignment.is_current = False
            if assignment.valid_to is None:
                assignment.valid_to = today

        db.add(
            AssetRoleAssignment(
                asset_role_id=target_role.id,
                asset_id=asset.id,
                assignment_type="primary",
                valid_from=today,
                valid_to=None,
                is_current=True,
                note="자산 목록 편집 모드에서 현재 역할 변경",
            )
        )

    summary = "현재 역할이 변경되었습니다."
    if target_role is None:
        detail = f"기존 역할: {', '.join(previous_role_names) if previous_role_names else '없음'}\n현재 역할이 해제되었습니다."
    else:
        detail = (
            f"기존 역할: {', '.join(previous_role_names) if previous_role_names else '없음'}\n"
            f"신규 역할: {target_role.role_name}"
        )
    log_asset_event(
        db,
        asset=asset,
        event_type="update",
        summary=summary,
        detail=detail,
        created_by_user_id=current_user.id,
    )
    db.commit()
    db.refresh(asset)
    return asset


# ── AssetContact ──


def list_asset_contacts(db: Session, asset_id: int) -> list[dict]:
    _ensure_asset_exists(db, asset_id)
    rows = list(
        db.execute(
            select(
                AssetContact,
                PartnerContact.name,
                PartnerContact.phone,
                PartnerContact.email,
            )
            .join(PartnerContact, PartnerContact.id == AssetContact.contact_id)
            .where(AssetContact.asset_id == asset_id)
            .order_by(AssetContact.id.asc())
        )
    )
    result = []
    for asset_contact, name, phone, email in rows:
        item = {
            "id": asset_contact.id,
            "asset_id": asset_contact.asset_id,
            "contact_id": asset_contact.contact_id,
            "contact_name": name,
            "contact_phone": phone,
            "contact_email": email,
            "role": asset_contact.role,
            "created_at": asset_contact.created_at,
            "updated_at": asset_contact.updated_at,
        }
        result.append(item)
    return result


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


def _ensure_period_belongs_to_partner(db: Session, period_id: int, partner_id: int) -> None:
    from app.modules.common.models.contract_period import ContractPeriod

    period = db.get(ContractPeriod, period_id)
    if period is None:
        raise NotFoundError("Contract period not found")
    period_partner_id = period.partner_id
    contract_partner_id = period.contract.end_partner_id if period.contract else None
    if period_partner_id != partner_id and contract_partner_id != partner_id:
        raise BusinessRuleError("선택한 귀속사업이 현재 고객사와 일치하지 않습니다.", status_code=422)


def _current_asset_period_id(db: Session, asset_id: int) -> int | None:
    from app.modules.infra.models.period_asset import PeriodAsset

    period_link = db.scalar(
        select(PeriodAsset).where(PeriodAsset.asset_id == asset_id).order_by(PeriodAsset.id.asc())
    )
    return period_link.contract_period_id if period_link is not None else None


def _build_classification_info(
    db: Session,
    catalog: ProductCatalog | None,
    *,
    period_id: int | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    layout_id: int | None = None,
    lang: str | None = None,
) -> dict[str, str | list[str | None] | bool | None]:
    if catalog is None:
        levels: list[str | None] = [None, None, None, None, None]
        parts: list[str] = []
        if category:
            parts.append(category)
            levels[0] = category
        if subcategory and subcategory != category:
            parts.append(subcategory)
            levels[1] = subcategory
        path = " > ".join(parts) if parts else None
        return {"path": path, "levels": levels, "is_fallback_text": bool(path)}

    use_kr = lang != "en"
    attrs = _get_catalog_attribute_map(db, catalog.id)
    layout = _get_effective_classification_layout(db, period_id=period_id, layout_id=layout_id)
    levels: list[str | None] = [None, None, None, None, None]
    if layout is None or not attrs:
        ordered = [attrs.get("domain"), attrs.get("imp_type"), attrs.get("product_family"), attrs.get("platform")]
        parts = [
            (item.get("label_kr") or item["label"]) if use_kr else item["label"]
            for item in ordered
            if item and item.get("label")
        ]
        for idx, part in enumerate(parts[:5]):
            levels[idx] = part
        return {"path": " > ".join(parts) if parts else None, "levels": levels, "is_fallback_text": False}

    parts: list[str] = []
    for idx, level in enumerate(layout["levels"][:5]):
        labels: list[str] = []
        joiner = level.get("joiner") or ", "
        for attribute_key in level["attribute_keys"]:
            item = attrs.get(attribute_key)
            if item and item.get("label"):
                labels.append((item.get("label_kr") or item["label"]) if use_kr else item["label"])
        if labels:
            part = joiner.join(labels)
            levels[idx] = part
            parts.append(part)
    return {"path": " > ".join(parts) if parts else None, "levels": levels, "is_fallback_text": False}


def _get_deepest_classification_label(levels: list[str | None]) -> str | None:
    for value in reversed(levels):
        if value:
            return value
    return None


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


def _resolve_physical_refs(
    db: Session,
    partner_id: int,
    center_id: int | None,
    room_id: int | None,
    rack_id: int | None,
) -> dict[str, int | str | None]:
    center = db.get(Center, center_id) if center_id else None
    room = db.get(Room, room_id) if room_id else None
    rack = db.get(Rack, rack_id) if rack_id else None

    if center is not None and center.partner_id != partner_id:
        raise BusinessRuleError("선택한 센터가 현재 고객사와 일치하지 않습니다.", status_code=422)
    if room is not None:
        if center is None:
            center = db.get(Center, room.center_id)
            center_id = center.id if center else None
        elif room.center_id != center.id:
            raise BusinessRuleError("선택한 전산실이 센터와 일치하지 않습니다.", status_code=422)
    if rack is not None:
        if room is None:
            room = db.get(Room, rack.room_id)
            room_id = room.id if room else None
        elif rack.room_id != room.id:
            raise BusinessRuleError("선택한 랙이 전산실과 일치하지 않습니다.", status_code=422)
        if center is None and room is not None:
            center = db.get(Center, room.center_id)
            center_id = center.id if center else None

    if center is not None and center.partner_id != partner_id:
        raise BusinessRuleError("선택한 물리배치 정보가 현재 고객사와 일치하지 않습니다.", status_code=422)

    return {
        "center_id": center.id if center else None,
        "room_id": room.id if room else None,
        "rack_id": rack.id if rack else None,
        "center_code": center.center_code if center else None,
        "rack_code": rack.rack_code if rack else None,
    }


_BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _to_base36(num: int, width: int = 4) -> str:
    if num == 0:
        return "0" * width
    result = ""
    while num:
        result = _BASE36_CHARS[num % 36] + result
        num //= 36
    return result.zfill(width)


def _generate_asset_code(db: Session, partner_id: int, type_code: str) -> str:
    """Generate asset code: {partner_code}-{type_code}-{base36 4자리}."""
    from app.modules.common.models.partner import Partner

    partner = db.get(Partner, partner_id)
    partner_code = partner.partner_code if partner else "X000"
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


def _get_catalog_asset_type_meta(
    db: Session,
    catalog: ProductCatalog,
    *,
    period_id: int | None = None,
) -> dict[str, str | None]:
    from app.modules.infra.services.product_catalog_attribute_service import get_product_attributes

    attr_values = get_product_attributes(db, catalog.id)
    attr_map = {
        item["attribute_key"]: item
        for item in attr_values
        if item.get("attribute_key")
    }
    if attr_map:
        layout = _get_effective_classification_layout(db, period_id=period_id)
        identity = derive_asset_type_identity(attr_map, layout)
        asset_kind = {
            "hw": "hardware",
            "sw": "software",
            "svc": "service",
        }.get(attr_map.get("imp_type", {}).get("option_key"))
        return {
            "asset_type_key": identity["asset_type_key"] if identity else None,
            "asset_type_code": identity["asset_type_code"] if identity else None,
            "asset_type_label": identity["asset_type_label"] if identity else None,
            "asset_kind": asset_kind,
        }
    return {"asset_type_key": None, "asset_type_code": None, "asset_type_label": None, "asset_kind": None}


def _get_catalog_attribute_map(db: Session, catalog_id: int) -> dict[str, dict[str, str | None]]:
    from app.modules.infra.services.product_catalog_attribute_service import get_product_attributes

    values = get_product_attributes(db, catalog_id)
    return {
        item["attribute_key"]: {
            "option_key": item.get("option_key"),
            "label": item.get("option_label") or item.get("option_key") or item.get("raw_value"),
            "label_kr": item.get("option_label_kr"),
        }
        for item in values
        if item.get("attribute_key")
    }


def _get_effective_classification_layout(
    db: Session,
    *,
    period_id: int | None,
    layout_id: int | None = None,
) -> dict | None:
    from app.modules.common.models.contract_period import ContractPeriod
    from app.modules.infra.models.classification_layout import ClassificationLayout
    from app.modules.infra.models.classification_layout_level import ClassificationLayoutLevel
    from app.modules.infra.models.classification_layout_level_key import ClassificationLayoutLevelKey

    # layout_id가 명시적으로 전달되면 우선 사용
    if layout_id is None and period_id is not None:
        period = db.get(ContractPeriod, period_id)
        if period is not None:
            layout_id = period.classification_layout_id
    stmt = (
        select(ClassificationLayout)
        .options(
            joinedload(ClassificationLayout.levels)
            .joinedload(ClassificationLayoutLevel.keys)
            .joinedload(ClassificationLayoutLevelKey.attribute)
        )
        .where(ClassificationLayout.is_active.is_(True))
    )
    if layout_id is not None:
        stmt = stmt.where(ClassificationLayout.id == layout_id)
    else:
        stmt = stmt.where(
            ClassificationLayout.scope_type == "global",
            ClassificationLayout.is_default.is_(True),
        ).order_by(ClassificationLayout.id.asc())
    layout = db.scalar(stmt)
    if layout is None:
        return None
    return {
        "id": layout.id,
        "levels": [
            {
                "level_no": level.level_no,
                "joiner": level.joiner,
                "attribute_keys": [
                    key.attribute.attribute_key
                    for key in sorted(level.keys, key=lambda item: (item.sort_order, item.id))
                    if key.is_visible and key.attribute is not None
                ],
            }
            for level in sorted(layout.levels, key=lambda item: (item.level_no, item.id))
        ],
    }

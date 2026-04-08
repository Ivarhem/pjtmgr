"""Infra module: asset event service tests."""
from __future__ import annotations

from app.modules.common.models.asset_type_code import AssetTypeCode
from app.modules.common.models.partner import Partner
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset import AssetCreate, AssetUpdate
from app.modules.infra.schemas.asset_event import AssetEventCreate
from app.modules.infra.services.asset_event_service import (
    create_asset_event,
    list_asset_events,
)
from app.modules.infra.services.asset_service import create_asset, update_asset


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _setup_asset(db):
    partner = Partner(partner_code="P001", name="이벤트고객")
    db.add(partner)
    db.flush()
    db.add(
        AssetTypeCode(
            type_key="server",
            code="SVR",
            label="서버",
            kind="hardware",
            sort_order=1,
            is_active=True,
        )
    )
    catalog = ProductCatalog(
        vendor="Dell",
        name="PowerEdge R760",
        product_type="hardware",
        category="서버",
        asset_type_key="server",
    )
    db.add(catalog)
    db.flush()
    return partner, catalog


def test_create_asset_logs_create_event(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, catalog = _setup_asset(db_session)

    asset = create_asset(
        db_session,
        AssetCreate(partner_id=partner.id, model_id=catalog.id, asset_name="EVT-01"),
        admin,
    )

    events = list_asset_events(db_session, asset.id)
    assert len(events) == 1
    assert events[0].event_type == "create"


def test_update_asset_logs_update_event(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, catalog = _setup_asset(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(partner_id=partner.id, model_id=catalog.id, asset_name="EVT-02"),
        admin,
    )

    update_asset(db_session, asset.id, AssetUpdate(status="active", location="Seoul"), admin)

    events = list_asset_events(db_session, asset.id)
    assert len(events) == 2
    assert events[0].event_type == "update"
    assert "status" in (events[0].detail or "")


def test_manual_asset_event_can_be_added(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, catalog = _setup_asset(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(partner_id=partner.id, model_id=catalog.id, asset_name="EVT-03"),
        admin,
    )

    create_asset_event(
        db_session,
        asset.id,
        AssetEventCreate(
            event_type="repurpose",
            summary="개발용으로 전환",
            detail="운영 종료 후 개발 검증 장비로 전환",
        ),
        admin,
    )

    events = list_asset_events(db_session, asset.id)
    assert len(events) == 2
    assert events[0].event_type == "repurpose"
    assert events[0].summary == "개발용으로 전환"


def test_asset_event_includes_related_asset_and_actor(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, catalog = _setup_asset(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(partner_id=partner.id, model_id=catalog.id, asset_name="EVT-04"),
        admin,
    )
    replacement_asset = create_asset(
        db_session,
        AssetCreate(partner_id=partner.id, model_id=catalog.id, asset_name="EVT-05"),
        admin,
    )

    create_asset_event(
        db_session,
        asset.id,
        AssetEventCreate(
            event_type="replacement",
            summary="대체 장비 투입",
            detail="장애 대응으로 교체",
            related_asset_id=replacement_asset.id,
        ),
        admin,
    )

    events = list_asset_events(db_session, asset.id)
    assert events[0].related_asset_id == replacement_asset.id
    assert events[0].related_asset_name == replacement_asset.asset_name
    assert events[0].related_asset_code == replacement_asset.system_id
    assert events[0].created_by_user_name == admin.name

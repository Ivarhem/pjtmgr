"""Infra module: asset service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.common.models.asset_type_code import AssetTypeCode
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.partner import Partner
from app.modules.infra.models.period_asset import PeriodAsset
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.center import Center
from app.modules.infra.models.room import Room
from app.modules.infra.models.rack import Rack
from app.modules.infra.models.asset_role import AssetRole
from app.modules.infra.models.asset_role_assignment import AssetRoleAssignment
from app.modules.infra.schemas.asset import AssetCreate, AssetUpdate
from app.modules.infra.services.asset_service import (
    create_asset,
    delete_asset,
    enrich_asset_with_catalog_kind,
    list_assets,
    update_asset_current_role,
    update_asset,
)


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_partner(db_session):
    partner = Partner(
        partner_code="P001",
        name="테스트고객",
        business_no="123-45-67890",
    )
    db_session.add(partner)
    db_session.flush()
    return partner


def _make_catalog(db_session, type_key: str = "server") -> ProductCatalog:
    db_session.add(
        AssetTypeCode(
            type_key=type_key,
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
        asset_type_key=type_key,
    )
    db_session.add(catalog)
    db_session.flush()
    return catalog


def _make_period(db_session, partner_id: int) -> ContractPeriod:
    contract = Contract(
        contract_code="C00000001",
        contract_name="테스트 프로젝트",
        contract_type="인프라",
        end_partner_id=partner_id,
        status="active",
    )
    db_session.add(contract)
    db_session.flush()
    period = ContractPeriod(
        contract_id=contract.id,
        period_year=2026,
        period_label="Y26",
        period_code="P000000000001",
        stage="active",
        partner_id=partner_id,
        is_completed=False,
        is_planned=False,
    )
    db_session.add(period)
    db_session.flush()
    return period


def _make_period_via_contract_partner_only(db_session, partner_id: int) -> ContractPeriod:
    contract = Contract(
        contract_code="C00000002",
        contract_name="종료고객사 기준 프로젝트",
        contract_type="인프라",
        end_partner_id=partner_id,
        status="active",
    )
    db_session.add(contract)
    db_session.flush()
    period = ContractPeriod(
        contract_id=contract.id,
        period_year=2027,
        period_label="Y27",
        period_code="P000000000002",
        stage="active",
        partner_id=None,
        is_completed=False,
        is_planned=False,
    )
    db_session.add(period)
    db_session.flush()
    return period


def test_create_and_list_assets(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)

    create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            project_asset_number="FW-INT-01",
            customer_asset_number="CUST-FW-01",
            asset_name="APP-01",
        ),
        admin,
    )

    assets = list_assets(db_session, partner_id=partner.id)
    assert len(assets) == 1
    assert assets[0].project_asset_number == "FW-INT-01"
    assert assets[0].customer_asset_number == "CUST-FW-01"
    assert assets[0].asset_name == "APP-01"
    assert assets[0].asset_type == "server"


def test_list_assets_can_search_project_asset_number(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)

    create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            project_asset_number="FW-INT-99",
            customer_asset_number="CUST-FW-99",
            asset_name="APP-99",
        ),
        admin,
    )

    assets = list_assets(db_session, partner_id=partner.id, q="FW-INT-99")
    assert len(assets) == 1
    assert assets[0].asset_name == "APP-99"


def test_list_assets_can_search_customer_asset_number(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)

    create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            customer_asset_number="CUST-APP-77",
            asset_name="APP-77",
        ),
        admin,
    )

    assets = list_assets(db_session, partner_id=partner.id, q="CUST-APP-77")
    assert len(assets) == 1
    assert assets[0].asset_name == "APP-77"


def test_create_asset_requires_existing_partner(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    catalog = _make_catalog(db_session)
    with pytest.raises(NotFoundError):
        create_asset(
            db_session,
            AssetCreate(
                partner_id=999,
                hardware_model_id=catalog.id,
                asset_name="APP-01",
            ),
            admin,
        )


def test_create_asset_rejects_duplicate_name_in_same_partner(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    payload = AssetCreate(
        partner_id=partner.id,
        hardware_model_id=catalog.id,
        asset_name="APP-01",
    )
    create_asset(db_session, payload, admin)

    with pytest.raises(DuplicateError):
        create_asset(db_session, payload, admin)


def test_update_and_delete_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            asset_name="APP-01",
        ),
        admin,
    )

    updated = update_asset(
        db_session,
        asset.id,
        AssetUpdate(status="active", location="Seoul"),
        admin,
    )
    assert updated.status == "active"
    assert updated.location == "Seoul"

    delete_asset(db_session, asset.id, admin)
    assert list_assets(db_session, partner_id=partner.id) == []


def test_update_asset_period_link(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    period = _make_period(db_session, partner.id)
    asset = create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            asset_name="APP-02",
        ),
        admin,
    )

    updated = update_asset(
        db_session,
        asset.id,
        AssetUpdate(period_id=period.id),
        admin,
    )

    link = db_session.query(PeriodAsset).filter(PeriodAsset.asset_id == asset.id).one()
    assert updated.id == asset.id
    assert link.contract_period_id == period.id


def test_enrich_asset_marks_raw_text_location_and_classification(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            asset_name="APP-RAW-01",
        ),
        admin,
    )

    updated = update_asset(
        db_session,
        asset.id,
        AssetUpdate(
            center="본사 IDC",
            rack_no="A-01",
            category="보안",
            subcategory="방화벽",
        ),
        admin,
    )

    enriched = enrich_asset_with_catalog_kind(db_session, updated)
    assert enriched["center_is_fallback_text"] is True
    assert enriched["rack_is_fallback_text"] is True
    assert enriched["classification_is_fallback_text"] is True
    assert enriched["classification_level_1_name"] == "보안"
    assert enriched["classification_level_2_name"] == "방화벽"


def test_update_asset_period_link_allows_contract_end_partner_period(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    period = _make_period_via_contract_partner_only(db_session, partner.id)
    asset = create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            asset_name="APP-02B",
        ),
        admin,
    )

    updated = update_asset(
        db_session,
        asset.id,
        AssetUpdate(period_id=period.id),
        admin,
    )

    link = db_session.query(PeriodAsset).filter(PeriodAsset.asset_id == asset.id).one()
    assert updated.id == asset.id
    assert link.contract_period_id == period.id


def test_update_asset_period_rejects_other_partner_period(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner_a = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(
            partner_id=partner_a.id,
            hardware_model_id=catalog.id,
            asset_name="APP-03",
        ),
        admin,
    )

    partner_b = Partner(partner_code="P002", name="다른고객")
    db_session.add(partner_b)
    db_session.flush()
    period_b = _make_period(db_session, partner_b.id)

    with pytest.raises(BusinessRuleError):
        update_asset(
            db_session,
            asset.id,
            AssetUpdate(period_id=period_b.id),
            admin,
        )


def test_update_asset_current_role(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            asset_name="APP-ROLE-01",
        ),
        admin,
    )
    role = AssetRole(
        partner_id=partner.id,
        role_name="인터넷방화벽#1",
        status="active",
    )
    db_session.add(role)
    db_session.flush()

    updated = update_asset_current_role(db_session, asset.id, role.id, admin)
    assignment = db_session.query(AssetRoleAssignment).filter_by(asset_id=asset.id, asset_role_id=role.id, is_current=True).one()

    assert updated.id == asset.id
    assert assignment.asset_role_id == role.id


def test_create_asset_with_physical_layout_refs(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    center = Center(partner_id=partner.id, center_code="CTR-001", center_name="A센터")
    db_session.add(center)
    db_session.flush()
    room = Room(center_id=center.id, room_code="MAIN", room_name="기본 전산실")
    db_session.add(room)
    db_session.flush()
    rack = Rack(room_id=room.id, rack_code="RACK-001", rack_name="메인 랙", total_units=42)
    db_session.add(rack)
    db_session.commit()

    asset = create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            asset_name="APP-LAYOUT-01",
            center_id=center.id,
            room_id=room.id,
            rack_id=rack.id,
        ),
        admin,
    )

    assert asset.center_id == center.id
    assert asset.room_id == room.id
    assert asset.rack_id == rack.id
    assert asset.center == "CTR-001"
    assert asset.rack_no == "RACK-001"


def test_clear_asset_current_role(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(
            partner_id=partner.id,
            hardware_model_id=catalog.id,
            asset_name="APP-ROLE-02",
        ),
        admin,
    )
    role = AssetRole(
        partner_id=partner.id,
        role_name="내부망방화벽",
        status="active",
    )
    db_session.add(role)
    db_session.flush()
    db_session.add(
        AssetRoleAssignment(
            asset_role_id=role.id,
            asset_id=asset.id,
            assignment_type="primary",
            is_current=True,
        )
    )
    db_session.commit()

    update_asset_current_role(db_session, asset.id, None, admin)
    assignments = db_session.query(AssetRoleAssignment).filter_by(asset_id=asset.id).all()

    assert assignments
    assert all(not assignment.is_current for assignment in assignments)

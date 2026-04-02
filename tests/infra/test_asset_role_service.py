"""Infra module: asset role foundation tests."""
from __future__ import annotations

from datetime import date

import pytest

from app.core.exceptions import BusinessRuleError
from app.modules.common.models.asset_type_code import AssetTypeCode
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.partner import Partner
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.asset_role import (
    AssetRoleAssignmentCreate,
    AssetRoleAssignmentUpdate,
    AssetRoleCreate,
)
from app.modules.infra.services.asset_role_service import (
    create_asset_role,
    create_asset_role_assignment,
    list_asset_role_assignments,
    list_asset_roles,
    replace_asset_role_assignment,
    repurpose_asset_role_assignment,
    update_asset_role_assignment,
)
from app.modules.infra.services.asset_event_service import list_asset_events
from app.modules.infra.services.asset_service import create_asset


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _setup(db, admin):
    partner = Partner(partner_code="P001", name="역할고객")
    other_partner = Partner(partner_code="P002", name="다른고객")
    db.add_all([partner, other_partner])
    db.flush()

    contract = Contract(
        contract_code="C00000001",
        contract_name="테스트사업",
        contract_type="인프라",
        end_partner_id=partner.id,
        status="active",
    )
    db.add(contract)
    db.flush()

    period = ContractPeriod(
        contract_id=contract.id,
        period_year=2026,
        period_label="Y26",
        period_code="P000000000099",
        stage="active",
        partner_id=partner.id,
        is_completed=False,
        is_planned=False,
    )
    db.add(period)
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

    asset_one = create_asset(
        db,
        AssetCreate(partner_id=partner.id, hardware_model_id=catalog.id, asset_name="SRV-01"),
        admin,
    )
    asset_two = create_asset(
        db,
        AssetCreate(partner_id=partner.id, hardware_model_id=catalog.id, asset_name="SRV-02"),
        admin,
    )
    other_asset = create_asset(
        db,
        AssetCreate(partner_id=other_partner.id, hardware_model_id=catalog.id, asset_name="SRV-99"),
        admin,
    )
    return partner, period, asset_one, asset_two, other_asset


def _setup_with_contract_partner_only_period(db, admin):
    partner = Partner(partner_code="P101", name="역할고객-종료고객사")
    db.add(partner)
    db.flush()

    contract = Contract(
        contract_code="C00000101",
        contract_name="종료고객사 기준 역할사업",
        contract_type="인프라",
        end_partner_id=partner.id,
        status="active",
    )
    db.add(contract)
    db.flush()

    period = ContractPeriod(
        contract_id=contract.id,
        period_year=2027,
        period_label="Y27",
        period_code="P000000001010",
        stage="active",
        partner_id=None,
        is_completed=False,
        is_planned=False,
    )
    db.add(period)
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

    asset_one = create_asset(
        db,
        AssetCreate(partner_id=partner.id, hardware_model_id=catalog.id, asset_name="SRV-CP-01"),
        admin,
    )
    return partner, period, asset_one


def test_create_role_and_current_assignment(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, period, asset_one, _, _ = _setup(db_session, admin)

    role = create_asset_role(
        db_session,
        AssetRoleCreate(
            partner_id=partner.id,
            contract_period_id=period.id,
            role_name="내부망방화벽",
            role_type="firewall",
        ),
        admin,
    )
    create_asset_role_assignment(
        db_session,
        role.id,
        AssetRoleAssignmentCreate(
            asset_id=asset_one.id,
            valid_from=date(2026, 3, 1),
            is_current=True,
        ),
        admin,
    )

    rows = list_asset_roles(db_session, partner.id)
    assert rows[0]["role_name"] == "내부망방화벽"
    assert rows[0]["current_asset_name"] == "SRV-01"


def test_create_role_allows_contract_end_partner_period(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, period, _asset_one = _setup_with_contract_partner_only_period(db_session, admin)

    role = create_asset_role(
        db_session,
        AssetRoleCreate(
            partner_id=partner.id,
            contract_period_id=period.id,
            role_name="종료고객사 기준 역할",
            role_type="firewall",
        ),
        admin,
    )

    assert role.contract_period_id == period.id


def test_new_current_assignment_clears_previous_current(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, period, asset_one, asset_two, _ = _setup(db_session, admin)

    role = create_asset_role(
        db_session,
        AssetRoleCreate(
            partner_id=partner.id,
            contract_period_id=period.id,
            role_name="외부망방화벽",
        ),
        admin,
    )
    first = create_asset_role_assignment(
        db_session,
        role.id,
        AssetRoleAssignmentCreate(asset_id=asset_one.id, is_current=True),
        admin,
    )
    second = create_asset_role_assignment(
        db_session,
        role.id,
        AssetRoleAssignmentCreate(asset_id=asset_two.id, is_current=True),
        admin,
    )

    rows = list_asset_role_assignments(db_session, role.id)
    by_id = {row["id"]: row for row in rows}
    assert by_id[first.id]["is_current"] is False
    assert by_id[second.id]["is_current"] is True


def test_assignment_partner_mismatch_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, period, _, _, other_asset = _setup(db_session, admin)

    role = create_asset_role(
        db_session,
        AssetRoleCreate(
            partner_id=partner.id,
            contract_period_id=period.id,
            role_name="개발 FW",
        ),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        create_asset_role_assignment(
            db_session,
            role.id,
            AssetRoleAssignmentCreate(asset_id=other_asset.id, is_current=True),
            admin,
        )


def test_update_assignment_valid_to_unsets_current(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, period, asset_one, _, _ = _setup(db_session, admin)

    role = create_asset_role(
        db_session,
        AssetRoleCreate(
            partner_id=partner.id,
            contract_period_id=period.id,
            role_name="운영 DB",
        ),
        admin,
    )
    assignment = create_asset_role_assignment(
        db_session,
        role.id,
        AssetRoleAssignmentCreate(asset_id=asset_one.id, is_current=True),
        admin,
    )

    updated = update_asset_role_assignment(
        db_session,
        assignment.id,
        AssetRoleAssignmentUpdate(valid_to=date(2026, 12, 31)),
        admin,
    )

    assert updated.is_current is False


def test_replacement_action_switches_current_assignment_and_logs_events(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, period, asset_one, asset_two, _ = _setup(db_session, admin)

    role = create_asset_role(
        db_session,
        AssetRoleCreate(
            partner_id=partner.id,
            contract_period_id=period.id,
            role_name="내부망방화벽",
        ),
        admin,
    )
    first = create_asset_role_assignment(
        db_session,
        role.id,
        AssetRoleAssignmentCreate(asset_id=asset_one.id, is_current=True),
        admin,
    )

    result = replace_asset_role_assignment(
        db_session,
        role.id,
        replacement_asset_id=asset_two.id,
        occurred_at=None,
        note="노후화 교체",
        current_user=admin,
        event_type="replacement",
    )

    rows = list_asset_role_assignments(db_session, role.id)
    by_id = {row["id"]: row for row in rows}
    assert by_id[first.id]["is_current"] is False
    assert any(row["asset_id"] == asset_two.id and row["is_current"] for row in rows)
    assert result["target_role_id"] == role.id
    old_events = list_asset_events(db_session, asset_one.id)
    new_events = list_asset_events(db_session, asset_two.id)
    assert old_events[0].event_type == "replacement"
    assert new_events[0].event_type == "replacement"


def test_failover_action_uses_temporary_assignment_type(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, period, asset_one, asset_two, _ = _setup(db_session, admin)

    role = create_asset_role(
        db_session,
        AssetRoleCreate(partner_id=partner.id, contract_period_id=period.id, role_name="외부망방화벽"),
        admin,
    )
    create_asset_role_assignment(
        db_session,
        role.id,
        AssetRoleAssignmentCreate(asset_id=asset_one.id, is_current=True),
        admin,
    )

    replace_asset_role_assignment(
        db_session,
        role.id,
        replacement_asset_id=asset_two.id,
        occurred_at=None,
        note="장애 대체",
        current_user=admin,
        event_type="failover",
    )

    rows = list_asset_role_assignments(db_session, role.id)
    current = next(row for row in rows if row["is_current"])
    assert current["asset_id"] == asset_two.id
    assert current["assignment_type"] == "temporary"


def test_repurpose_action_creates_new_role_and_moves_current_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner, period, asset_one, _, _ = _setup(db_session, admin)

    role = create_asset_role(
        db_session,
        AssetRoleCreate(partner_id=partner.id, contract_period_id=period.id, role_name="운영 FW"),
        admin,
    )
    create_asset_role_assignment(
        db_session,
        role.id,
        AssetRoleAssignmentCreate(asset_id=asset_one.id, is_current=True),
        admin,
    )

    result = repurpose_asset_role_assignment(
        db_session,
        role.id,
        new_role_name="개발 FW",
        new_role_type="firewall",
        new_contract_period_id=period.id,
        occurred_at=None,
        note="개발 검증용 전환",
        current_user=admin,
    )

    roles = list_asset_roles(db_session, partner.id)
    source = next(item for item in roles if item["id"] == role.id)
    target = next(item for item in roles if item["id"] == result["target_role_id"])
    assert source["current_asset_id"] is None
    assert target["current_asset_id"] == asset_one.id
    events = list_asset_events(db_session, asset_one.id)
    assert events[0].event_type == "repurpose"

"""Infra module: period-asset link service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.customer import Customer
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.period_asset import PeriodAssetCreate, PeriodAssetUpdate
from app.modules.infra.services.period_asset_service import (
    create_period_asset,
    list_by_asset,
    list_by_period,
    delete_period_asset,
    update_period_asset,
)
from app.modules.infra.services.asset_service import create_asset


def _make_admin(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="pa_admin", name="PAAdmin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_customer(db_session):
    customer = Customer(name="테스트고객", business_no="123-45-67890")
    db_session.add(customer)
    db_session.flush()
    return customer


def _make_period(db_session, customer_id: int, code: str = "PA") -> ContractPeriod:
    contract = Contract(
        contract_name=f"{code} Contract",
        contract_type="인프라",
        end_customer_id=customer_id,
    )
    db_session.add(contract)
    db_session.flush()
    period = ContractPeriod(
        contract_id=contract.id,
        period_year=2025,
        period_label="Y25",
        stage="50%",
        customer_id=customer_id,
    )
    db_session.add(period)
    db_session.commit()
    db_session.refresh(period)
    return period


def test_link_and_list(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    customer = _make_customer(db_session)
    period = _make_period(db_session, customer.id, "PA-01")
    asset = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="SVR-01", asset_type="server"), admin)

    pa = create_period_asset(db_session, PeriodAssetCreate(contract_period_id=period.id, asset_id=asset.id, role="primary"), admin)
    assert pa.contract_period_id == period.id
    assert pa.asset_id == asset.id

    by_period = list_by_period(db_session, period.id)
    assert len(by_period) == 1
    assert by_period[0]["asset_name"] == "SVR-01"

    by_asset = list_by_asset(db_session, asset.id)
    assert len(by_asset) == 1


def test_duplicate_link_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    customer = _make_customer(db_session)
    period = _make_period(db_session, customer.id, "PA-02")
    asset = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="SVR-02", asset_type="server"), admin)

    create_period_asset(db_session, PeriodAssetCreate(contract_period_id=period.id, asset_id=asset.id), admin)
    with pytest.raises(DuplicateError):
        create_period_asset(db_session, PeriodAssetCreate(contract_period_id=period.id, asset_id=asset.id), admin)


def test_unlink(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    customer = _make_customer(db_session)
    period = _make_period(db_session, customer.id, "PA-03")
    asset = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="SVR-03", asset_type="server"), admin)

    pa = create_period_asset(db_session, PeriodAssetCreate(contract_period_id=period.id, asset_id=asset.id), admin)
    delete_period_asset(db_session, pa.id, admin)
    assert len(list_by_period(db_session, period.id)) == 0


def test_update_role(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    customer = _make_customer(db_session)
    period = _make_period(db_session, customer.id, "PA-04")
    asset = create_asset(db_session, AssetCreate(customer_id=customer.id, asset_name="SVR-04", asset_type="server"), admin)

    pa = create_period_asset(db_session, PeriodAssetCreate(contract_period_id=period.id, asset_id=asset.id), admin)
    updated = update_period_asset(db_session, pa.id, PeriodAssetUpdate(role="backup"), admin)
    assert updated.role == "backup"

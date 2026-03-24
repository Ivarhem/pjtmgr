"""Infra module: period-partner link service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.infra.schemas.period_partner import (
    PeriodPartnerCreate,
    PeriodPartnerUpdate,
)
from app.modules.infra.services.period_partner_service import (
    create_period_partner,
    delete_period_partner,
    list_by_period,
    update_period_partner,
)


def _make_admin(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="pc_admin", name="PCAdmin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_partner(db_session, name: str = "TestCorp", bno: str = "123-45-67890"):
    from app.modules.common.models.partner import Partner

    c = Partner(name=name, business_no=bno)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def _make_period(db_session, partner_id: int, code: str = "PC") -> ContractPeriod:
    contract = Contract(
        contract_name=f"{code} Contract",
        contract_type="인프라",
        end_partner_id=partner_id,
    )
    db_session.add(contract)
    db_session.flush()
    period = ContractPeriod(
        contract_id=contract.id,
        period_year=2025,
        period_label="Y25",
        stage="50%",
        partner_id=partner_id,
    )
    db_session.add(period)
    db_session.commit()
    db_session.refresh(period)
    return period


def test_create_and_list(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust = _make_partner(db_session)
    period = _make_period(db_session, cust.id, "PC-01")

    pc = create_period_partner(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="고객사"
        ),
        admin,
    )
    assert pc.contract_period_id == period.id
    assert pc.partner_id == cust.id
    assert pc.role == "고객사"

    items = list_by_period(db_session, period.id)
    assert len(items) == 1
    assert items[0]["partner_name"] == "TestCorp"
    assert items[0]["business_no"] == "123-45-67890"


def test_duplicate_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust = _make_partner(db_session, name="DupCorp", bno="111-11-11111")
    period = _make_period(db_session, cust.id, "PC-02")

    create_period_partner(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="수행사"
        ),
        admin,
    )
    with pytest.raises(DuplicateError):
        create_period_partner(
            db_session,
            PeriodPartnerCreate(
                contract_period_id=period.id, partner_id=cust.id, role="수행사"
            ),
            admin,
        )


def test_same_partner_different_role_allowed(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust = _make_partner(db_session, name="MultiCorp", bno="222-22-22222")
    period = _make_period(db_session, cust.id, "PC-03")

    create_period_partner(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="고객사"
        ),
        admin,
    )
    pc2 = create_period_partner(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="유지보수사"
        ),
        admin,
    )
    assert pc2.role == "유지보수사"
    assert len(list_by_period(db_session, period.id)) == 2


def test_update(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust = _make_partner(db_session, name="UpdCorp", bno="333-33-33333")
    period = _make_period(db_session, cust.id, "PC-04")

    pc = create_period_partner(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="벤더"
        ),
        admin,
    )
    updated = update_period_partner(
        db_session,
        pc.id,
        PeriodPartnerUpdate(scope_text="HW 납품"),
        admin,
    )
    assert updated.scope_text == "HW 납품"


def test_delete(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust = _make_partner(db_session, name="DelCorp", bno="444-44-44444")
    period = _make_period(db_session, cust.id, "PC-05")

    pc = create_period_partner(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="통신사"
        ),
        admin,
    )
    delete_period_partner(db_session, pc.id, admin)
    assert len(list_by_period(db_session, period.id)) == 0


def test_not_found_period(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust = _make_partner(db_session, name="NfCorp", bno="555-55-55555")

    with pytest.raises(NotFoundError):
        create_period_partner(
            db_session,
            PeriodPartnerCreate(
                contract_period_id=99999, partner_id=cust.id, role="고객사"
            ),
            admin,
        )

"""Infra module: period-partner-contact link service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.infra.schemas.period_partner import PeriodPartnerCreate
from app.modules.infra.schemas.period_partner_contact import (
    PeriodPartnerContactCreate,
    PeriodPartnerContactUpdate,
)
from app.modules.infra.services.period_partner_service import (
    create_period_partner as create_pc,
)
from app.modules.infra.services.period_partner_contact_service import (
    create_period_partner_contact,
    delete_period_partner_contact,
    list_by_period,
    list_by_period_partner,
    update_period_partner_contact,
)


def _make_admin(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="pcc_admin", name="PCCAdmin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_partner_and_contact(db_session):
    from app.modules.common.models.partner import Partner
    from app.modules.common.models.partner_contact import PartnerContact

    c = Partner(name="ContactTestCorp", business_no="999-99-99999")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    ct = PartnerContact(partner_id=c.id, name="홍길동", phone="010-1234-5678", email="hong@test.com")
    db_session.add(ct)
    db_session.commit()
    db_session.refresh(ct)
    return c, ct


def _make_period(db_session, partner_id: int, code: str = "PCC") -> ContractPeriod:
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
    cust, contact = _make_partner_and_contact(db_session)
    period = _make_period(db_session, cust.id, "PCC-01")

    pc = create_pc(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="고객사"
        ),
        admin,
    )

    pcc = create_period_partner_contact(
        db_session,
        PeriodPartnerContactCreate(
            period_partner_id=pc.id,
            contact_id=contact.id,
            project_role="고객PM",
        ),
        admin,
    )
    assert pcc.period_partner_id == pc.id
    assert pcc.contact_id == contact.id
    assert pcc.project_role == "고객PM"

    items = list_by_period_partner(db_session, pc.id)
    assert len(items) == 1
    assert items[0]["contact_name"] == "홍길동"
    assert items[0]["contact_phone"] == "010-1234-5678"

    # list_by_period
    all_items = list_by_period(db_session, period.id)
    assert len(all_items) == 1


def test_duplicate_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_partner_and_contact(db_session)
    period = _make_period(db_session, cust.id, "PCC-02")
    pc = create_pc(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="수행사"
        ),
        admin,
    )

    create_period_partner_contact(
        db_session,
        PeriodPartnerContactCreate(
            period_partner_id=pc.id,
            contact_id=contact.id,
            project_role="수행PM",
        ),
        admin,
    )
    with pytest.raises(DuplicateError):
        create_period_partner_contact(
            db_session,
            PeriodPartnerContactCreate(
                period_partner_id=pc.id,
                contact_id=contact.id,
                project_role="수행PM",
            ),
            admin,
        )


def test_same_contact_different_role_allowed(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_partner_and_contact(db_session)
    period = _make_period(db_session, cust.id, "PCC-03")
    pc = create_pc(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="고객사"
        ),
        admin,
    )

    create_period_partner_contact(
        db_session,
        PeriodPartnerContactCreate(
            period_partner_id=pc.id,
            contact_id=contact.id,
            project_role="고객PM",
        ),
        admin,
    )
    pcc2 = create_period_partner_contact(
        db_session,
        PeriodPartnerContactCreate(
            period_partner_id=pc.id,
            contact_id=contact.id,
            project_role="승인자",
        ),
        admin,
    )
    assert pcc2.project_role == "승인자"
    assert len(list_by_period_partner(db_session, pc.id)) == 2


def test_update(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_partner_and_contact(db_session)
    period = _make_period(db_session, cust.id, "PCC-04")
    pc = create_pc(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="벤더"
        ),
        admin,
    )
    pcc = create_period_partner_contact(
        db_session,
        PeriodPartnerContactCreate(
            period_partner_id=pc.id,
            contact_id=contact.id,
            project_role="구축엔지니어",
        ),
        admin,
    )
    updated = update_period_partner_contact(
        db_session,
        pcc.id,
        PeriodPartnerContactUpdate(note="주간보고 참석"),
        admin,
    )
    assert updated.note == "주간보고 참석"


def test_delete(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_partner_and_contact(db_session)
    period = _make_period(db_session, cust.id, "PCC-05")
    pc = create_pc(
        db_session,
        PeriodPartnerCreate(
            contract_period_id=period.id, partner_id=cust.id, role="통신사"
        ),
        admin,
    )
    pcc = create_period_partner_contact(
        db_session,
        PeriodPartnerContactCreate(
            period_partner_id=pc.id,
            contact_id=contact.id,
            project_role="유지보수담당",
        ),
        admin,
    )
    delete_period_partner_contact(db_session, pcc.id, admin)
    assert len(list_by_period_partner(db_session, pc.id)) == 0

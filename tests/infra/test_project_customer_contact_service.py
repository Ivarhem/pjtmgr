"""Infra module: project-customer-contact link service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.infra.schemas.project import ProjectCreate
from app.modules.infra.schemas.project_customer import ProjectCustomerCreate
from app.modules.infra.schemas.project_customer_contact import (
    ProjectCustomerContactCreate,
    ProjectCustomerContactUpdate,
)
from app.modules.infra.services.project_customer_service import (
    create_project_customer as create_pc,
)
from app.modules.infra.services.project_customer_contact_service import (
    create_project_customer_contact,
    delete_project_customer_contact,
    list_by_project,
    list_by_project_customer,
    update_project_customer_contact,
)
from app.modules.infra.services.project_service import create_project


def _make_admin(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="pcc_admin", name="PCCAdmin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_customer_and_contact(db_session):
    from app.modules.common.models.customer import Customer
    from app.modules.common.models.customer_contact import CustomerContact

    c = Customer(name="ContactTestCorp", business_no="999-99-99999")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)

    ct = CustomerContact(customer_id=c.id, name="홍길동", phone="010-1234-5678", email="hong@test.com")
    db_session.add(ct)
    db_session.commit()
    db_session.refresh(ct)
    return c, ct


def test_create_and_list(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_customer_and_contact(db_session)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PCC-01", project_name="Contact Test", customer_id=cust.id),
        admin,
    )

    pc = create_pc(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="고객사"
        ),
        admin,
    )

    pcc = create_project_customer_contact(
        db_session,
        ProjectCustomerContactCreate(
            project_customer_id=pc.id,
            contact_id=contact.id,
            project_role="고객PM",
        ),
        admin,
    )
    assert pcc.project_customer_id == pc.id
    assert pcc.contact_id == contact.id
    assert pcc.project_role == "고객PM"

    items = list_by_project_customer(db_session, pc.id)
    assert len(items) == 1
    assert items[0]["contact_name"] == "홍길동"
    assert items[0]["contact_phone"] == "010-1234-5678"

    # list_by_project
    all_items = list_by_project(db_session, proj.id)
    assert len(all_items) == 1


def test_duplicate_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_customer_and_contact(db_session)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PCC-02", project_name="Dup Contact", customer_id=cust.id),
        admin,
    )
    pc = create_pc(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="수행사"
        ),
        admin,
    )

    create_project_customer_contact(
        db_session,
        ProjectCustomerContactCreate(
            project_customer_id=pc.id,
            contact_id=contact.id,
            project_role="수행PM",
        ),
        admin,
    )
    with pytest.raises(DuplicateError):
        create_project_customer_contact(
            db_session,
            ProjectCustomerContactCreate(
                project_customer_id=pc.id,
                contact_id=contact.id,
                project_role="수행PM",
            ),
            admin,
        )


def test_same_contact_different_role_allowed(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_customer_and_contact(db_session)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PCC-03", project_name="Multi Role", customer_id=cust.id),
        admin,
    )
    pc = create_pc(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="고객사"
        ),
        admin,
    )

    create_project_customer_contact(
        db_session,
        ProjectCustomerContactCreate(
            project_customer_id=pc.id,
            contact_id=contact.id,
            project_role="고객PM",
        ),
        admin,
    )
    pcc2 = create_project_customer_contact(
        db_session,
        ProjectCustomerContactCreate(
            project_customer_id=pc.id,
            contact_id=contact.id,
            project_role="승인자",
        ),
        admin,
    )
    assert pcc2.project_role == "승인자"
    assert len(list_by_project_customer(db_session, pc.id)) == 2


def test_update(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_customer_and_contact(db_session)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PCC-04", project_name="Update Contact", customer_id=cust.id),
        admin,
    )
    pc = create_pc(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="벤더"
        ),
        admin,
    )
    pcc = create_project_customer_contact(
        db_session,
        ProjectCustomerContactCreate(
            project_customer_id=pc.id,
            contact_id=contact.id,
            project_role="구축엔지니어",
        ),
        admin,
    )
    updated = update_project_customer_contact(
        db_session,
        pcc.id,
        ProjectCustomerContactUpdate(note="주간보고 참석"),
        admin,
    )
    assert updated.note == "주간보고 참석"


def test_delete(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust, contact = _make_customer_and_contact(db_session)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PCC-05", project_name="Del Contact", customer_id=cust.id),
        admin,
    )
    pc = create_pc(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="통신사"
        ),
        admin,
    )
    pcc = create_project_customer_contact(
        db_session,
        ProjectCustomerContactCreate(
            project_customer_id=pc.id,
            contact_id=contact.id,
            project_role="유지보수담당",
        ),
        admin,
    )
    delete_project_customer_contact(db_session, pcc.id, admin)
    assert len(list_by_project_customer(db_session, pc.id)) == 0

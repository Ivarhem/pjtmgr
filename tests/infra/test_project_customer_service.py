"""Infra module: project-customer link service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.infra.schemas.project import ProjectCreate
from app.modules.infra.schemas.project_customer import (
    ProjectCustomerCreate,
    ProjectCustomerUpdate,
)
from app.modules.infra.services.project_customer_service import (
    create,
    delete,
    list_by_project,
    update,
)
from app.modules.infra.services.project_service import create_project


def _make_admin(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="pc_admin", name="PCAdmin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_customer(db_session, name: str = "TestCorp", bno: str = "123-45-67890"):
    from app.modules.common.models.customer import Customer

    c = Customer(name=name, business_no=bno)
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def test_create_and_list(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PC-01", project_name="Cust Link Test"),
        admin,
    )
    cust = _make_customer(db_session)

    pc = create(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="고객사"
        ),
        admin,
    )
    assert pc.project_id == proj.id
    assert pc.customer_id == cust.id
    assert pc.role == "고객사"

    items = list_by_project(db_session, proj.id)
    assert len(items) == 1
    assert items[0]["customer_name"] == "TestCorp"
    assert items[0]["business_no"] == "123-45-67890"


def test_duplicate_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PC-02", project_name="Dup Test"),
        admin,
    )
    cust = _make_customer(db_session, name="DupCorp", bno="111-11-11111")

    create(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="수행사"
        ),
        admin,
    )
    with pytest.raises(DuplicateError):
        create(
            db_session,
            ProjectCustomerCreate(
                project_id=proj.id, customer_id=cust.id, role="수행사"
            ),
            admin,
        )


def test_same_customer_different_role_allowed(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PC-03", project_name="Multi Role Test"),
        admin,
    )
    cust = _make_customer(db_session, name="MultiCorp", bno="222-22-22222")

    create(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="고객사"
        ),
        admin,
    )
    pc2 = create(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="유지보수사"
        ),
        admin,
    )
    assert pc2.role == "유지보수사"
    assert len(list_by_project(db_session, proj.id)) == 2


def test_update(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PC-04", project_name="Update Test"),
        admin,
    )
    cust = _make_customer(db_session, name="UpdCorp", bno="333-33-33333")

    pc = create(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="벤더"
        ),
        admin,
    )
    updated = update(
        db_session,
        pc.id,
        ProjectCustomerUpdate(scope_text="HW 납품"),
        admin,
    )
    assert updated.scope_text == "HW 납품"


def test_delete(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(
        db_session,
        ProjectCreate(project_code="PC-05", project_name="Del Test"),
        admin,
    )
    cust = _make_customer(db_session, name="DelCorp", bno="444-44-44444")

    pc = create(
        db_session,
        ProjectCustomerCreate(
            project_id=proj.id, customer_id=cust.id, role="통신사"
        ),
        admin,
    )
    delete(db_session, pc.id, admin)
    assert len(list_by_project(db_session, proj.id)) == 0


def test_not_found_project(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    cust = _make_customer(db_session, name="NfCorp", bno="555-55-55555")

    with pytest.raises(NotFoundError):
        create(
            db_session,
            ProjectCustomerCreate(
                project_id=99999, customer_id=cust.id, role="고객사"
            ),
            admin,
        )

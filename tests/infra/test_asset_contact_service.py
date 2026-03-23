"""Infra module: asset contact service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.customer import Customer
from app.modules.common.models.customer_contact import CustomerContact
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.asset_contact import AssetContactCreate, AssetContactUpdate
from app.modules.infra.services.asset_service import (
    create_asset,
    create_asset_contact,
    delete_asset_contact,
    get_asset_contact,
    list_asset_contacts,
    update_asset_contact,
)


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _setup(db, admin):
    """Create customer, asset, and customer contact for tests."""
    customer = Customer(name="ABC Corp")
    db.add(customer)
    db.flush()

    asset = create_asset(
        db,
        AssetCreate(
            customer_id=customer.id, asset_name="SRV-01", asset_type="server"
        ),
        admin,
    )

    contact = CustomerContact(
        customer_id=customer.id, name="홍길동", contact_type=""
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    return asset, customer, contact


def test_create_and_list_asset_contacts(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, _, contact = _setup(db_session, admin)

    create_asset_contact(
        db_session,
        AssetContactCreate(
            asset_id=asset.id, contact_id=contact.id, role="운영담당"
        ),
        admin,
    )

    acs = list_asset_contacts(db_session, asset.id)
    assert len(acs) == 1
    assert acs[0].role == "운영담당"


def test_create_asset_contact_rejects_duplicate(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, _, contact = _setup(db_session, admin)

    create_asset_contact(
        db_session,
        AssetContactCreate(
            asset_id=asset.id, contact_id=contact.id, role="운영담당"
        ),
        admin,
    )

    with pytest.raises(DuplicateError):
        create_asset_contact(
            db_session,
            AssetContactCreate(
                asset_id=asset.id, contact_id=contact.id, role="운영담당"
            ),
            admin,
        )


def test_same_contact_different_roles_allowed(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, _, contact = _setup(db_session, admin)

    create_asset_contact(
        db_session,
        AssetContactCreate(
            asset_id=asset.id, contact_id=contact.id, role="운영담당"
        ),
        admin,
    )
    create_asset_contact(
        db_session,
        AssetContactCreate(
            asset_id=asset.id, contact_id=contact.id, role="보안담당"
        ),
        admin,
    )

    acs = list_asset_contacts(db_session, asset.id)
    assert len(acs) == 2


def test_update_asset_contact(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, _, contact = _setup(db_session, admin)

    ac = create_asset_contact(
        db_session,
        AssetContactCreate(
            asset_id=asset.id, contact_id=contact.id, role="운영담당"
        ),
        admin,
    )

    updated = update_asset_contact(
        db_session, ac.id, AssetContactUpdate(role="보안담당"), admin
    )

    assert updated.role == "보안담당"


def test_delete_asset_contact(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    asset, _, contact = _setup(db_session, admin)

    ac = create_asset_contact(
        db_session,
        AssetContactCreate(
            asset_id=asset.id, contact_id=contact.id, role="운영담당"
        ),
        admin,
    )

    delete_asset_contact(db_session, ac.id, admin)

    with pytest.raises(NotFoundError):
        get_asset_contact(db_session, ac.id)

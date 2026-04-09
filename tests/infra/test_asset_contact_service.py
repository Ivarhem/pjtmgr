"""Infra module: asset contact service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.asset_type_code import AssetTypeCode
from app.modules.common.models.partner import Partner
from app.modules.common.models.partner_contact import PartnerContact
from app.modules.infra.models.product_catalog import ProductCatalog
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
    """Create partner, asset, and partner contact for tests."""
    partner = Partner(partner_code="P001", name="ABC Corp")
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

    asset = create_asset(
        db,
        AssetCreate(
            partner_id=partner.id,
            model_id=catalog.id,
            asset_name="SRV-01",
        ),
        admin,
    )

    contact = PartnerContact(
        partner_id=partner.id,
        name="홍길동",
        phone="010-1111-2222",
        email="hong@example.com",
        contact_type="",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    return asset, partner, contact


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
    assert acs[0]["role"] == "운영담당"
    assert acs[0]["contact_name"] == "홍길동"
    assert acs[0]["contact_phone"] == "010-1111-2222"


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

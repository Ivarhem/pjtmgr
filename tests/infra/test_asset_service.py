"""Infra module: asset service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.partner import Partner
from app.modules.infra.schemas.asset import AssetCreate, AssetUpdate
from app.modules.infra.services.asset_service import (
    create_asset,
    delete_asset,
    list_assets,
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
    partner = Partner(name="테스트고객", business_no="123-45-67890")
    db_session.add(partner)
    db_session.flush()
    return partner


def test_create_and_list_assets(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)

    create_asset(
        db_session,
        AssetCreate(partner_id=partner.id, asset_name="APP-01", asset_type="server"),
        admin,
    )

    assets = list_assets(db_session, partner_id=partner.id)
    assert len(assets) == 1
    assert assets[0].asset_name == "APP-01"


def test_create_asset_requires_existing_partner(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_asset(
            db_session,
            AssetCreate(partner_id=999, asset_name="APP-01", asset_type="server"),
            admin,
        )


def test_create_asset_rejects_duplicate_name_in_same_partner(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    payload = AssetCreate(
        partner_id=partner.id, asset_name="APP-01", asset_type="server"
    )
    create_asset(db_session, payload, admin)

    with pytest.raises(DuplicateError):
        create_asset(db_session, payload, admin)


def test_update_and_delete_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = create_asset(
        db_session,
        AssetCreate(partner_id=partner.id, asset_name="APP-01", asset_type="server"),
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

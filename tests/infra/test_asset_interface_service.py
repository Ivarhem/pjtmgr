"""Infra module: AssetInterface service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.common.models.partner import Partner
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset_interface import (
    AssetInterfaceCreate,
    AssetInterfaceUpdate,
)
from app.modules.infra.services.asset_interface_service import (
    create_interface,
    delete_interface,
    get_interface,
    list_interfaces,
    set_lag_members,
    update_interface,
)


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin_if", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_partner(db_session, name="테스트고객", bno="123-45-67890", code="T001"):
    partner = Partner(name=name, business_no=bno, partner_code=code)
    db_session.add(partner)
    db_session.flush()
    return partner


def _make_catalog(db_session, vendor="TestVendor", name="TestModel"):
    catalog = ProductCatalog(vendor=vendor, name=name, product_type="hardware")
    db_session.add(catalog)
    db_session.flush()
    return catalog


def _make_asset(db, partner_id: int, name: str, admin):
    catalog = _make_catalog(db, name=f"Model-{name}")
    asset = Asset(
        partner_id=partner_id,
        asset_name=name,
        model_id=catalog.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


# -- Tests --


def test_create_and_list_interfaces(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0", if_type="physical"),
        admin,
    )
    create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth1", if_type="physical"),
        admin,
    )

    interfaces = list_interfaces(db_session, asset.id)
    assert len(interfaces) == 2


def test_create_interface_requires_existing_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_interface(
            db_session,
            AssetInterfaceCreate(asset_id=9999, name="eth0"),
            admin,
        )


def test_create_interface_duplicate_name_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0"),
        admin,
    )
    with pytest.raises(DuplicateError):
        create_interface(
            db_session,
            AssetInterfaceCreate(asset_id=asset.id, name="eth0"),
            admin,
        )


def test_update_interface(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    iface = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0"),
        admin,
    )

    updated = update_interface(
        db_session,
        iface.id,
        AssetInterfaceUpdate(speed="10G", media_type="SFP+"),
        admin,
    )

    assert updated.speed == "10G"
    assert updated.media_type == "SFP+"


def test_delete_interface(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    iface = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0"),
        admin,
    )

    delete_interface(db_session, iface.id, admin)

    with pytest.raises(NotFoundError):
        get_interface(db_session, iface.id)


def test_set_lag_members(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    eth0 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0", if_type="physical"),
        admin,
    )
    eth1 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth1", if_type="physical"),
        admin,
    )
    bond0 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="bond0", if_type="lag"),
        admin,
    )

    set_lag_members(db_session, bond0.id, [eth0.id, eth1.id], admin)

    db_session.refresh(eth0)
    db_session.refresh(eth1)
    assert eth0.parent_id == bond0.id
    assert eth1.parent_id == bond0.id


def test_lag_member_must_be_same_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset1 = _make_asset(db_session, partner.id, "SRV-01", admin)
    asset2 = _make_asset(db_session, partner.id, "SRV-02", admin)

    eth0 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset2.id, name="eth0", if_type="physical"),
        admin,
    )
    bond0 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset1.id, name="bond0", if_type="lag"),
        admin,
    )

    with pytest.raises(BusinessRuleError, match="same asset"):
        set_lag_members(db_session, bond0.id, [eth0.id], admin)


def test_lag_member_must_be_physical_type(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    lag1 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="bond0", if_type="lag"),
        admin,
    )
    lag2 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="bond1", if_type="lag"),
        admin,
    )

    with pytest.raises(BusinessRuleError, match="physical"):
        set_lag_members(db_session, lag1.id, [lag2.id], admin)

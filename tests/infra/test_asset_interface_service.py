"""Infra module: AssetInterface service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.common.models.partner import Partner
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset_interface import (
    AssetInterfaceCreate,
    AssetInterfaceUpdate,
)
from app.modules.infra.services.asset_interface_service import (
    create_interface,
    delete_interface,
    generate_interfaces_from_catalog,
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


# -- Catalog auto-generation tests --


def _make_catalog_with_interfaces(db_session):
    """카탈로그 + HardwareInterface 스펙 생성 헬퍼."""
    catalog = ProductCatalog(vendor="Cisco", name="C9300-48T")
    db_session.add(catalog)
    db_session.flush()

    hw1 = HardwareInterface(
        product_id=catalog.id,
        interface_type="1GE",
        speed="1G",
        count=4,
        connector_type="copper",
        capacity_type="fixed",
    )
    hw2 = HardwareInterface(
        product_id=catalog.id,
        interface_type="10GE",
        speed="10G",
        count=2,
        connector_type="sfp+",
        capacity_type="modular",
        note="Slot 1",
    )
    db_session.add_all([hw1, hw2])
    db_session.flush()
    return catalog


def test_generate_interfaces_from_catalog(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog_with_interfaces(db_session)

    # Create asset and manually set model_id to our catalog with HW interfaces
    asset = _make_asset(db_session, partner.id, "SW-01", admin)
    asset.model_id = catalog.id
    db_session.commit()

    created = generate_interfaces_from_catalog(db_session, asset.id, admin)

    assert len(created) == 6  # 4 fixed + 2 modular
    modular = [c for c in created if c.oper_status == "not_present"]
    fixed = [c for c in created if c.oper_status is None]
    assert len(fixed) == 4
    assert len(modular) == 2
    assert all(f.speed == "1G" for f in fixed)
    assert all(m.speed == "10G" for m in modular)


def test_generate_no_hw_specs_returns_empty(db_session, admin_role_id) -> None:
    """카탈로그에 HardwareInterface 스펙이 없으면 빈 리스트를 반환한다."""
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    # _make_asset creates a catalog with no HardwareInterface specs
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    created = generate_interfaces_from_catalog(db_session, asset.id, admin)
    assert len(created) == 0


def test_generate_idempotent(db_session, admin_role_id) -> None:
    """이미 동일 이름 인터페이스가 있으면 건너뛴다."""
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog_with_interfaces(db_session)

    asset = _make_asset(db_session, partner.id, "SW-01", admin)
    asset.model_id = catalog.id
    db_session.commit()

    first = generate_interfaces_from_catalog(db_session, asset.id, admin)
    second = generate_interfaces_from_catalog(db_session, asset.id, admin)

    assert len(first) == 6
    assert len(second) == 0  # skip duplicates

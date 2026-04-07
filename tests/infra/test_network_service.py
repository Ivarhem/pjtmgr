"""Infra module: network service tests (IpSubnet, AssetIP)."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.common.models.partner import Partner
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_interface import AssetInterface
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset_ip import AssetIPCreate, AssetIPUpdate
from app.modules.infra.schemas.ip_subnet import IpSubnetCreate, IpSubnetUpdate
from app.modules.infra.services.network_service import (
    create_asset_ip,
    create_subnet,
    delete_asset_ip,
    delete_subnet,
    get_asset_ip,
    get_subnet,
    list_asset_ips,
    list_subnets,
    update_asset_ip,
    update_subnet,
)


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


_partner_seq = 0


def _make_partner(db_session, name="테스트고객", bno="123-45-67890"):
    global _partner_seq
    _partner_seq += 1
    partner = Partner(name=name, business_no=bno, partner_code=f"P{_partner_seq:03d}")
    db_session.add(partner)
    db_session.flush()
    return partner


_catalog_seq = 0


def _make_catalog(db_session, vendor: str = "TestVendor", name: str = "TestModel"):
    global _catalog_seq
    _catalog_seq += 1
    catalog = ProductCatalog(
        vendor=vendor, name=f"{name}-{_catalog_seq}", product_type="hardware"
    )
    db_session.add(catalog)
    db_session.flush()
    return catalog


def _make_asset(db, partner_id: int, name: str, admin):
    catalog = _make_catalog(db, name=f"Model-{name}")
    asset = Asset(partner_id=partner_id, asset_name=name, model_id=catalog.id)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _make_interface(db, asset_id: int, name: str = "eth0") -> AssetInterface:
    iface = AssetInterface(asset_id=asset_id, name=name, if_type="physical")
    db.add(iface)
    db.flush()
    return iface


# -- IpSubnet tests --


def test_create_and_list_subnets(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)

    create_subnet(
        db_session,
        IpSubnetCreate(
            partner_id=partner.id,
            name="서비스망-A",
            subnet="10.10.1.0/24",
            role="service",
            region="서울",
        ),
        admin,
    )
    create_subnet(
        db_session,
        IpSubnetCreate(
            partner_id=partner.id,
            name="관리망-A",
            subnet="10.10.2.0/24",
            role="management",
        ),
        admin,
    )

    subnets = list_subnets(db_session, partner_id=partner.id)
    assert len(subnets) == 2


def test_create_subnet_requires_existing_partner(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_subnet(
            db_session,
            IpSubnetCreate(partner_id=9999, name="test", subnet="10.0.0.0/24"),
            admin,
        )


def test_update_subnet(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(partner_id=partner.id, name="서비스망", subnet="10.10.1.0/24"),
        admin,
    )

    updated = update_subnet(
        db_session,
        subnet.id,
        IpSubnetUpdate(region="부산DR", floor="3F", counterpart="XX은행 부산지점"),
        admin,
    )

    assert updated.region == "부산DR"
    assert updated.floor == "3F"
    assert updated.counterpart == "XX은행 부산지점"


def test_delete_subnet_blocked_with_assigned_ips(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(partner_id=partner.id, name="서비스망", subnet="10.10.1.0/24"),
        admin,
    )
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)
    iface = _make_interface(db_session, asset.id)
    create_asset_ip(
        db_session,
        AssetIPCreate(
            interface_id=iface.id, ip_subnet_id=subnet.id, ip_address="10.10.1.10"
        ),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        delete_subnet(db_session, subnet.id, admin)


def test_delete_subnet_without_ips(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(partner_id=partner.id, name="서비스망", subnet="10.10.1.0/24"),
        admin,
    )

    delete_subnet(db_session, subnet.id, admin)

    with pytest.raises(NotFoundError):
        get_subnet(db_session, subnet.id)


# -- AssetIP tests --


def test_create_and_list_asset_ips(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)
    iface = _make_interface(db_session, asset.id)

    create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface.id, ip_address="10.10.1.10", ip_type="service"),
        admin,
    )
    create_asset_ip(
        db_session,
        AssetIPCreate(
            interface_id=iface.id, ip_address="10.10.2.10", ip_type="management"
        ),
        admin,
    )

    ips = list_asset_ips(db_session, asset.id)
    assert len(ips) == 2


def test_create_asset_ip_requires_existing_interface(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_asset_ip(
            db_session,
            AssetIPCreate(interface_id=9999, ip_address="10.10.1.10"),
            admin,
        )


def test_create_asset_ip_with_subnet_reference(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)
    iface = _make_interface(db_session, asset.id)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(partner_id=partner.id, name="서비스망", subnet="10.10.1.0/24"),
        admin,
    )

    ip = create_asset_ip(
        db_session,
        AssetIPCreate(
            interface_id=iface.id, ip_subnet_id=subnet.id, ip_address="10.10.1.10"
        ),
        admin,
    )

    assert ip.ip_subnet_id == subnet.id


def test_create_asset_ip_rejects_nonexistent_subnet(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)
    iface = _make_interface(db_session, asset.id)

    with pytest.raises(NotFoundError):
        create_asset_ip(
            db_session,
            AssetIPCreate(
                interface_id=iface.id, ip_subnet_id=9999, ip_address="10.10.1.10"
            ),
            admin,
        )


def test_ip_duplicate_rejected_within_same_partner(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset1 = _make_asset(db_session, partner.id, "SRV-01", admin)
    asset2 = _make_asset(db_session, partner.id, "SRV-02", admin)
    iface1 = _make_interface(db_session, asset1.id)
    iface2 = _make_interface(db_session, asset2.id)

    create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface1.id, ip_address="10.10.1.10"),
        admin,
    )

    with pytest.raises(DuplicateError):
        create_asset_ip(
            db_session,
            AssetIPCreate(interface_id=iface2.id, ip_address="10.10.1.10"),
            admin,
        )


def test_ip_duplicate_allowed_across_partners(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner1 = _make_partner(db_session, name="고객1", bno="111-11-11111")
    partner2 = _make_partner(db_session, name="고객2", bno="222-22-22222")
    asset1 = _make_asset(db_session, partner1.id, "SRV-01", admin)
    asset2 = _make_asset(db_session, partner2.id, "SRV-01", admin)
    iface1 = _make_interface(db_session, asset1.id)
    iface2 = _make_interface(db_session, asset2.id)

    create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface1.id, ip_address="10.10.1.10"),
        admin,
    )
    ip2 = create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface2.id, ip_address="10.10.1.10"),
        admin,
    )

    assert ip2.ip_address == "10.10.1.10"


def test_update_asset_ip(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)
    iface = _make_interface(db_session, asset.id)
    ip = create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface.id, ip_address="10.10.1.10"),
        admin,
    )

    updated = update_asset_ip(
        db_session,
        ip.id,
        AssetIPUpdate(ip_type="management", is_primary=True),
        admin,
    )

    assert updated.ip_type == "management"
    assert updated.is_primary is True


def test_update_asset_ip_rejects_duplicate_address(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)
    iface = _make_interface(db_session, asset.id)
    create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface.id, ip_address="10.10.1.10"),
        admin,
    )
    ip2 = create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface.id, ip_address="10.10.1.20"),
        admin,
    )

    with pytest.raises(DuplicateError):
        update_asset_ip(
            db_session, ip2.id, AssetIPUpdate(ip_address="10.10.1.10"), admin
        )


def test_delete_asset_ip(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)
    iface = _make_interface(db_session, asset.id)
    ip = create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface.id, ip_address="10.10.1.10"),
        admin,
    )

    delete_asset_ip(db_session, ip.id, admin)

    with pytest.raises(NotFoundError):
        get_asset_ip(db_session, ip.id)

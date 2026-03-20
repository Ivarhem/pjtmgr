"""Infra module: network service tests (IpSubnet, AssetIP)."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.common.models.customer import Customer
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.asset_ip import AssetIPCreate, AssetIPUpdate
from app.modules.infra.schemas.ip_subnet import IpSubnetCreate, IpSubnetUpdate
from app.modules.infra.schemas.project import ProjectCreate
from app.modules.infra.services.asset_service import create_asset
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
from app.modules.infra.services.project_service import create_project


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_customer(db_session, name="테스트고객", bno="123-45-67890"):
    customer = Customer(name=name, business_no=bno)
    db_session.add(customer)
    db_session.flush()
    return customer


def _make_project(db, admin, customer):
    return create_project(
        db,
        ProjectCreate(project_code="PRJ-001", project_name="Test", customer_id=customer.id),
        admin,
    )


def _make_asset(db, customer_id: int, name: str, admin):
    return create_asset(
        db,
        AssetCreate(customer_id=customer_id, asset_name=name, asset_type="server"),
        admin,
    )


# ── IpSubnet tests ──


def test_create_and_list_subnets(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)

    create_subnet(
        db_session,
        IpSubnetCreate(
            customer_id=customer.id,
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
            customer_id=customer.id,
            name="관리망-A",
            subnet="10.10.2.0/24",
            role="management",
        ),
        admin,
    )

    subnets = list_subnets(db_session, customer_id=customer.id)
    assert len(subnets) == 2


def test_create_subnet_requires_existing_customer(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_subnet(
            db_session,
            IpSubnetCreate(customer_id=9999, name="test", subnet="10.0.0.0/24"),
            admin,
        )


def test_update_subnet(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(customer_id=customer.id, name="서비스망", subnet="10.10.1.0/24"),
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
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(customer_id=customer.id, name="서비스망", subnet="10.10.1.0/24"),
        admin,
    )
    asset = _make_asset(db_session, customer.id, "SRV-01", admin)
    create_asset_ip(
        db_session,
        AssetIPCreate(
            asset_id=asset.id, ip_subnet_id=subnet.id, ip_address="10.10.1.10"
        ),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        delete_subnet(db_session, subnet.id, admin)


def test_delete_subnet_without_ips(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(customer_id=customer.id, name="서비스망", subnet="10.10.1.0/24"),
        admin,
    )

    delete_subnet(db_session, subnet.id, admin)

    with pytest.raises(NotFoundError):
        get_subnet(db_session, subnet.id)


# ── AssetIP tests ──


def test_create_and_list_asset_ips(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    asset = _make_asset(db_session, customer.id, "SRV-01", admin)

    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.10", ip_type="service"),
        admin,
    )
    create_asset_ip(
        db_session,
        AssetIPCreate(
            asset_id=asset.id, ip_address="10.10.2.10", ip_type="management"
        ),
        admin,
    )

    ips = list_asset_ips(db_session, asset.id)
    assert len(ips) == 2


def test_create_asset_ip_requires_existing_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_asset_ip(
            db_session,
            AssetIPCreate(asset_id=9999, ip_address="10.10.1.10"),
            admin,
        )


def test_create_asset_ip_with_subnet_reference(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    asset = _make_asset(db_session, customer.id, "SRV-01", admin)
    subnet = create_subnet(
        db_session,
        IpSubnetCreate(customer_id=customer.id, name="서비스망", subnet="10.10.1.0/24"),
        admin,
    )

    ip = create_asset_ip(
        db_session,
        AssetIPCreate(
            asset_id=asset.id, ip_subnet_id=subnet.id, ip_address="10.10.1.10"
        ),
        admin,
    )

    assert ip.ip_subnet_id == subnet.id


def test_create_asset_ip_rejects_nonexistent_subnet(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    asset = _make_asset(db_session, customer.id, "SRV-01", admin)

    with pytest.raises(NotFoundError):
        create_asset_ip(
            db_session,
            AssetIPCreate(
                asset_id=asset.id, ip_subnet_id=9999, ip_address="10.10.1.10"
            ),
            admin,
        )


def test_ip_duplicate_rejected_within_same_customer(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    asset1 = _make_asset(db_session, customer.id, "SRV-01", admin)
    asset2 = _make_asset(db_session, customer.id, "SRV-02", admin)

    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset1.id, ip_address="10.10.1.10"),
        admin,
    )

    with pytest.raises(DuplicateError):
        create_asset_ip(
            db_session,
            AssetIPCreate(asset_id=asset2.id, ip_address="10.10.1.10"),
            admin,
        )


def test_ip_duplicate_allowed_across_customers(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer1 = _make_customer(db_session, name="고객1", bno="111-11-11111")
    customer2 = _make_customer(db_session, name="고객2", bno="222-22-22222")
    project1 = _make_project(db_session, admin, customer1)
    project2 = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-002", project_name="Test2", customer_id=customer2.id),
        admin,
    )
    asset1 = _make_asset(db_session, customer1.id, "SRV-01", admin)
    asset2 = create_asset(
        db_session,
        AssetCreate(
            customer_id=customer2.id, asset_name="SRV-01", asset_type="server"
        ),
        admin,
    )

    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset1.id, ip_address="10.10.1.10"),
        admin,
    )
    ip2 = create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset2.id, ip_address="10.10.1.10"),
        admin,
    )

    assert ip2.ip_address == "10.10.1.10"


def test_update_asset_ip(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    asset = _make_asset(db_session, customer.id, "SRV-01", admin)
    ip = create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.10"),
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
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    asset = _make_asset(db_session, customer.id, "SRV-01", admin)
    create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.10"),
        admin,
    )
    ip2 = create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.20"),
        admin,
    )

    with pytest.raises(DuplicateError):
        update_asset_ip(
            db_session, ip2.id, AssetIPUpdate(ip_address="10.10.1.10"), admin
        )


def test_delete_asset_ip(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    customer = _make_customer(db_session)
    project = _make_project(db_session, admin, customer)
    asset = _make_asset(db_session, customer.id, "SRV-01", admin)
    ip = create_asset_ip(
        db_session,
        AssetIPCreate(asset_id=asset.id, ip_address="10.10.1.10"),
        admin,
    )

    delete_asset_ip(db_session, ip.id, admin)

    with pytest.raises(NotFoundError):
        get_asset_ip(db_session, ip.id)

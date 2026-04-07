"""Infra module: port map service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import NotFoundError
from app.modules.common.models.partner import Partner
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_interface import AssetInterface
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.port_map import PortMapCreate, PortMapUpdate
from app.modules.infra.services.network_service import (
    create_port_map,
    delete_port_map,
    get_port_map,
    list_port_maps,
    update_port_map,
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
    partner = Partner(name=name, business_no=bno, partner_code=f"Z{_partner_seq:03d}")
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


def test_create_and_list_port_maps(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    src_asset = _make_asset(db_session, partner.id, "WEB-01", admin)
    dst_asset = _make_asset(db_session, partner.id, "DB-01", admin)
    src_iface = _make_interface(db_session, src_asset.id, "eth0")
    dst_iface = _make_interface(db_session, dst_asset.id, "eth0")

    create_port_map(
        db_session,
        PortMapCreate(
            partner_id=partner.id,
            src_interface_id=src_iface.id,
            dst_interface_id=dst_iface.id,
            protocol="tcp",
            port=5432,
            purpose="PostgreSQL",
        ),
        admin,
    )

    maps = list_port_maps(db_session, partner_id=partner.id)
    assert len(maps) == 1
    assert maps[0].port == 5432
    assert maps[0].purpose == "PostgreSQL"


def test_create_port_map_requires_existing_partner(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_port_map(
            db_session,
            PortMapCreate(partner_id=9999, port=443),
            admin,
        )


def test_create_port_map_with_nullable_interfaces(db_session, admin_role_id) -> None:
    """External segment: src/dst interface not specified."""
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)

    pm = create_port_map(
        db_session,
        PortMapCreate(
            partner_id=partner.id,
            port=443,
            purpose="External HTTPS",
        ),
        admin,
    )

    assert pm.src_interface_id is None
    assert pm.dst_interface_id is None


def test_create_port_map_rejects_nonexistent_src_interface(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)

    with pytest.raises(NotFoundError):
        create_port_map(
            db_session,
            PortMapCreate(
                partner_id=partner.id,
                src_interface_id=9999,
                port=80,
            ),
            admin,
        )


def test_create_port_map_rejects_nonexistent_dst_interface(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)

    with pytest.raises(NotFoundError):
        create_port_map(
            db_session,
            PortMapCreate(
                partner_id=partner.id,
                dst_interface_id=9999,
                port=80,
            ),
            admin,
        )


def test_update_port_map(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    pm = create_port_map(
        db_session,
        PortMapCreate(partner_id=partner.id, port=80, purpose="HTTP"),
        admin,
    )

    updated = update_port_map(
        db_session,
        pm.id,
        PortMapUpdate(port=443, protocol="tcp", purpose="HTTPS", status="approved"),
        admin,
    )

    assert updated.port == 443
    assert updated.purpose == "HTTPS"
    assert updated.status == "approved"


def test_update_port_map_rejects_nonexistent_interface(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    pm = create_port_map(
        db_session,
        PortMapCreate(partner_id=partner.id, port=80, purpose="HTTP"),
        admin,
    )

    with pytest.raises(NotFoundError):
        update_port_map(
            db_session,
            pm.id,
            PortMapUpdate(src_interface_id=9999),
            admin,
        )


def test_delete_port_map(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    pm = create_port_map(
        db_session,
        PortMapCreate(partner_id=partner.id, port=22, purpose="SSH"),
        admin,
    )

    delete_port_map(db_session, pm.id, admin)

    with pytest.raises(NotFoundError):
        get_port_map(db_session, pm.id)

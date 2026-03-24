"""Infra module: port map service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.common.models.partner import Partner
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.port_map import PortMapCreate, PortMapUpdate
from app.modules.infra.services.asset_service import create_asset
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


def _make_partner(db_session, name="테스트고객", bno="123-45-67890"):
    partner = Partner(name=name, business_no=bno)
    db_session.add(partner)
    db_session.flush()
    return partner


def _make_asset(db, partner_id: int, name: str, admin):
    return create_asset(
        db,
        AssetCreate(partner_id=partner_id, asset_name=name, asset_type="server"),
        admin,
    )


def test_create_and_list_port_maps(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    src = _make_asset(db_session, partner.id, "WEB-01", admin)
    dst = _make_asset(db_session, partner.id, "DB-01", admin)

    create_port_map(
        db_session,
        PortMapCreate(
            partner_id=partner.id,
            src_asset_id=src.id,
            src_ip="10.10.1.10",
            dst_asset_id=dst.id,
            dst_ip="10.10.1.20",
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


def test_create_port_map_with_nullable_assets(db_session, admin_role_id) -> None:
    """External segment: src/dst asset not specified, only IPs."""
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)

    pm = create_port_map(
        db_session,
        PortMapCreate(
            partner_id=partner.id,
            src_ip="203.0.113.1",
            dst_ip="10.10.1.10",
            port=443,
            purpose="External HTTPS",
        ),
        admin,
    )

    assert pm.src_asset_id is None
    assert pm.dst_asset_id is None
    assert pm.src_ip == "203.0.113.1"


def test_create_port_map_rejects_asset_from_other_partner(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner1 = _make_partner(db_session, name="고객1", bno="111-11-11111")
    partner2 = _make_partner(db_session, name="고객2", bno="222-22-22222")
    asset_other = _make_asset(db_session, partner2.id, "SRV-OTHER", admin)

    with pytest.raises(BusinessRuleError):
        create_port_map(
            db_session,
            PortMapCreate(
                partner_id=partner1.id,
                src_asset_id=asset_other.id,
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

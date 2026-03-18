"""Infra module: port map service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.port_map import PortMapCreate, PortMapUpdate
from app.modules.infra.schemas.project import ProjectCreate
from app.modules.infra.services.asset_service import create_asset
from app.modules.infra.services.network_service import (
    create_port_map,
    delete_port_map,
    get_port_map,
    list_port_maps,
    update_port_map,
)
from app.modules.infra.services.project_service import create_project


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_project(db, admin):
    return create_project(
        db,
        ProjectCreate(project_code="PRJ-001", project_name="Test"),
        admin,
    )


def _make_asset(db, project_id: int, name: str, admin):
    return create_asset(
        db,
        AssetCreate(project_id=project_id, asset_name=name, asset_type="server"),
        admin,
    )


def test_create_and_list_port_maps(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    project = _make_project(db_session, admin)
    src = _make_asset(db_session, project.id, "WEB-01", admin)
    dst = _make_asset(db_session, project.id, "DB-01", admin)

    create_port_map(
        db_session,
        PortMapCreate(
            project_id=project.id,
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

    maps = list_port_maps(db_session, project.id)
    assert len(maps) == 1
    assert maps[0].port == 5432
    assert maps[0].purpose == "PostgreSQL"


def test_create_port_map_requires_existing_project(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_port_map(
            db_session,
            PortMapCreate(project_id=9999, port=443),
            admin,
        )


def test_create_port_map_with_nullable_assets(db_session, admin_role_id) -> None:
    """External segment: src/dst asset not specified, only IPs."""
    admin = _make_admin_user(db_session, admin_role_id)
    project = _make_project(db_session, admin)

    pm = create_port_map(
        db_session,
        PortMapCreate(
            project_id=project.id,
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


def test_create_port_map_rejects_asset_from_other_project(
    db_session, admin_role_id
) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    project1 = _make_project(db_session, admin)
    project2 = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-002", project_name="Other"),
        admin,
    )
    asset_other = _make_asset(db_session, project2.id, "SRV-OTHER", admin)

    with pytest.raises(BusinessRuleError):
        create_port_map(
            db_session,
            PortMapCreate(
                project_id=project1.id,
                src_asset_id=asset_other.id,
                port=80,
            ),
            admin,
        )


def test_update_port_map(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    project = _make_project(db_session, admin)
    pm = create_port_map(
        db_session,
        PortMapCreate(project_id=project.id, port=80, purpose="HTTP"),
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
    project = _make_project(db_session, admin)
    pm = create_port_map(
        db_session,
        PortMapCreate(project_id=project.id, port=22, purpose="SSH"),
        admin,
    )

    delete_port_map(db_session, pm.id, admin)

    with pytest.raises(NotFoundError):
        get_port_map(db_session, pm.id)

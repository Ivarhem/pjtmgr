"""Infra module: project-asset link service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.infra.schemas.project import ProjectCreate
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.project_asset import ProjectAssetCreate, ProjectAssetUpdate
from app.modules.infra.services.project_asset_service import (
    backfill_from_legacy,
    create_project_asset,
    list_by_asset,
    list_by_project,
    delete_project_asset,
    update_project_asset,
)
from app.modules.infra.services.project_service import create_project
from app.modules.infra.services.asset_service import create_asset


def _make_admin(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="pa_admin", name="PAAdmin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_link_and_list(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(db_session, ProjectCreate(project_code="PA-01", project_name="Link Test"), admin)
    asset = create_asset(db_session, AssetCreate(project_id=proj.id, asset_name="SVR-01", asset_type="server"), admin)

    pa = create_project_asset(db_session, ProjectAssetCreate(project_id=proj.id, asset_id=asset.id, role="primary"), admin)
    assert pa.project_id == proj.id
    assert pa.asset_id == asset.id

    by_proj = list_by_project(db_session, proj.id)
    assert len(by_proj) == 1
    assert by_proj[0]["asset_name"] == "SVR-01"

    by_asset = list_by_asset(db_session, asset.id)
    assert len(by_asset) == 1
    assert by_asset[0]["project_code"] == "PA-01"


def test_duplicate_link_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(db_session, ProjectCreate(project_code="PA-02", project_name="Dup Test"), admin)
    asset = create_asset(db_session, AssetCreate(project_id=proj.id, asset_name="SVR-02", asset_type="server"), admin)

    create_project_asset(db_session, ProjectAssetCreate(project_id=proj.id, asset_id=asset.id), admin)
    with pytest.raises(DuplicateError):
        create_project_asset(db_session, ProjectAssetCreate(project_id=proj.id, asset_id=asset.id), admin)


def test_unlink(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(db_session, ProjectCreate(project_code="PA-03", project_name="Unlink Test"), admin)
    asset = create_asset(db_session, AssetCreate(project_id=proj.id, asset_name="SVR-03", asset_type="server"), admin)

    pa = create_project_asset(db_session, ProjectAssetCreate(project_id=proj.id, asset_id=asset.id), admin)
    delete_project_asset(db_session, pa.id, admin)
    assert len(list_by_project(db_session, proj.id)) == 0


def test_update_role(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(db_session, ProjectCreate(project_code="PA-04", project_name="Update Test"), admin)
    asset = create_asset(db_session, AssetCreate(project_id=proj.id, asset_name="SVR-04", asset_type="server"), admin)

    pa = create_project_asset(db_session, ProjectAssetCreate(project_id=proj.id, asset_id=asset.id), admin)
    updated = update_project_asset(db_session, pa.id, ProjectAssetUpdate(role="backup"), admin)
    assert updated.role == "backup"


def test_backfill(db_session, admin_role_id) -> None:
    admin = _make_admin(db_session, admin_role_id)
    proj = create_project(db_session, ProjectCreate(project_code="PA-05", project_name="Backfill Test"), admin)
    create_asset(db_session, AssetCreate(project_id=proj.id, asset_name="SVR-05", asset_type="server"), admin)
    create_asset(db_session, AssetCreate(project_id=proj.id, asset_name="SVR-06", asset_type="server"), admin)

    count = backfill_from_legacy(db_session)
    assert count >= 2

    # 재실행 시 중복 생성 없음
    count2 = backfill_from_legacy(db_session)
    assert count2 == 0

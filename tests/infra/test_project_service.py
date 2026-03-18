"""Infra module: project service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError
from app.modules.infra.schemas.project import ProjectCreate, ProjectUpdate
from app.modules.infra.services.project_service import (
    create_project,
    delete_project,
    list_projects,
    update_project,
)


def _make_admin_user(db_session, admin_role_id: int):
    """Create a real admin user in the DB for authorization checks."""
    from app.modules.common.models.user import User

    user = User(login_id="admin", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_create_and_list_projects(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)

    create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory"),
        admin,
    )

    projects = list_projects(db_session)
    assert len(projects) == 1
    assert projects[0].project_code == "PRJ-001"


def test_create_project_rejects_duplicate_code(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    payload = ProjectCreate(project_code="PRJ-001", project_name="Inventory")
    create_project(db_session, payload, admin)

    with pytest.raises(DuplicateError):
        create_project(db_session, payload, admin)


def test_delete_project_with_assets_is_blocked(db_session, admin_role_id) -> None:
    from app.modules.infra.schemas.asset import AssetCreate
    from app.modules.infra.services.asset_service import create_asset

    admin = _make_admin_user(db_session, admin_role_id)

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory"),
        admin,
    )
    create_asset(
        db_session,
        AssetCreate(project_id=project.id, asset_name="APP-01", asset_type="server"),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        delete_project(db_session, project.id, admin)


def test_update_project_changes_fields(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)

    project = create_project(
        db_session,
        ProjectCreate(project_code="PRJ-001", project_name="Inventory"),
        admin,
    )

    updated = update_project(
        db_session,
        project.id,
        ProjectUpdate(project_name="Updated Inventory", status="active"),
        admin,
    )

    assert updated.project_name == "Updated Inventory"
    assert updated.status == "active"

from app.modules.common.schemas.user import UserCreate, UserUpdate
from app.modules.common.services.user import create_user, list_users, update_user


def test_create_user_with_permission_flags_creates_matching_role(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(
            name="권한사용자",
            login_id="perm-user@example.com",
            permissions={
                "common_manage": True,
                "accounting_use": True,
                "accounting_manage": False,
                "infra_use": True,
                "infra_manage": False,
            },
        ),
    )

    assert user["role_permissions"]["common"]["manage"] is True
    assert user["role_permissions"]["modules"]["accounting"] == "full"
    assert user["role_permissions"]["scopes"]["accounting"] == "own"
    assert user["role_permissions"]["modules"]["infra"] == "read"
    assert "공통관리" in user["permission_tags"]
    assert "영업사용" in user["permission_tags"]
    assert "프로젝트사용" in user["permission_tags"]


def test_update_user_permissions_promotes_scope_and_tags(db_session) -> None:
    user = create_user(
        db_session,
        UserCreate(
            name="프로젝트사용자",
            login_id="infra-user@example.com",
            permissions={
                "accounting_use": True,
                "infra_use": True,
            },
        ),
    )

    updated = update_user(
        db_session,
        user["id"],
        UserUpdate(
            permissions={
                "common_manage": True,
                "accounting_use": True,
                "accounting_manage": True,
                "infra_use": True,
                "infra_manage": True,
            }
        ),
    )

    assert updated["role_permissions"]["common"]["manage"] is True
    assert updated["role_permissions"]["scopes"]["accounting"] == "all"
    assert updated["role_permissions"]["modules"]["infra"] == "full"
    assert "영업관리" in updated["permission_tags"]
    assert "프로젝트관리" in updated["permission_tags"]


def test_list_users_returns_permission_tags(db_session) -> None:
    create_user(
        db_session,
        UserCreate(
            name="태그사용자",
            login_id="tag-user@example.com",
            permissions={
                "accounting_use": True,
            },
        ),
    )

    rows = list_users(db_session)
    row = next(item for item in rows if item["login_id"] == "tag-user@example.com")
    assert row["permission_tags"] == ["영업사용"]

from datetime import UTC, datetime, timedelta

import pytest

from app.auth.password import hash_password
from app.auth.service import authenticate, change_password, reset_login_failures
from app.models.login_failure import LoginFailure
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.setting import update_setting
from app.services.user import create_user, ensure_bootstrap_admin
from app.exceptions import BusinessRuleError


def test_authenticate_locks_after_repeated_failures(db_session, monkeypatch) -> None:
    user = User(
        name="테스터",
        login_id="tester",
        role="user",
        is_active=True,
        hashed_password=hash_password("secret123"),
    )
    db_session.add(user)
    db_session.commit()

    now = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr("app.auth.service._now", lambda: now)
    reset_login_failures(db_session)

    for _ in range(5):
        assert authenticate(db_session, "tester", "wrong") is None

    # 잠김 상태 — 올바른 비밀번호로도 실패
    assert authenticate(db_session, "tester", "secret123") is None

    # 잠금 시간 경과 후 성공
    monkeypatch.setattr("app.auth.service._now", lambda: now + timedelta(minutes=16))
    assert authenticate(db_session, "tester", "secret123") is not None

    reset_login_failures(db_session)


def test_change_password_uses_setting_password_min_length(db_session) -> None:
    user = User(
        name="테스터",
        login_id="tester",
        role="user",
        is_active=True,
        hashed_password=hash_password("secret123"),
    )
    db_session.add(user)
    db_session.commit()
    update_setting(db_session, "auth.password_min_length", "10")

    with pytest.raises(BusinessRuleError, match="10자 이상"):
        change_password(db_session, user, "secret123", "short123")


def test_login_failure_persists_in_db(db_session, monkeypatch) -> None:
    """로그인 실패 기록이 DB에 영속되는지 확인."""
    user = User(
        name="테스터",
        login_id="persist-test",
        role="user",
        is_active=True,
        hashed_password=hash_password("secret123"),
    )
    db_session.add(user)
    db_session.commit()

    now = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr("app.auth.service._now", lambda: now)

    # 3회 실패
    for _ in range(3):
        authenticate(db_session, "persist-test", "wrong")

    # DB에 실패 기록 확인
    row = db_session.query(LoginFailure).filter(LoginFailure.login_id == "persist-test").first()
    assert row is not None
    assert row.failure_count == 3

    # 성공 시 실패 기록 삭제
    authenticate(db_session, "persist-test", "secret123")
    row = db_session.query(LoginFailure).filter(LoginFailure.login_id == "persist-test").first()
    assert row is None


def test_bootstrap_admin_rejects_short_password(db_session) -> None:
    """환경변수 비밀번호가 최소 길이 미만이면 BusinessRuleError."""
    with pytest.raises(BusinessRuleError, match="이상이어야"):
        ensure_bootstrap_admin(
            db_session, login_id="admin", password="short", name="관리자"
        )


def test_create_user_warns_short_login_id(db_session, caplog) -> None:
    """login_id가 최소 길이 미만이면 경고 로그 기록."""
    import logging

    with caplog.at_level(logging.WARNING, logger="app.services.user"):
        create_user(db_session, UserCreate(name="짧은ID", login_id="ab", role="user"))
    assert any("최소 길이" in r.message for r in caplog.records)

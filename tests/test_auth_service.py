from datetime import UTC, datetime, timedelta

from app.auth.password import hash_password
from app.auth.service import authenticate, change_password, reset_login_failures
from app.models.user import User
from app.services.setting import update_setting
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
    reset_login_failures()

    for _ in range(5):
        assert authenticate(db_session, "tester", "wrong") is None

    assert authenticate(db_session, "tester", "secret123") is None

    monkeypatch.setattr("app.auth.service._now", lambda: now + timedelta(minutes=16))
    assert authenticate(db_session, "tester", "secret123") is not None

    reset_login_failures()


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

    try:
        change_password(db_session, user, "secret123", "short123")
    except BusinessRuleError as exc:
        assert "10자 이상" in str(exc)
    else:
        raise AssertionError("BusinessRuleError was not raised")

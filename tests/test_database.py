from app.database import _engine_kwargs
from app.config import PASSWORD_MIN_LENGTH, SESSION_COOKIE_NAME, SESSION_HTTPS_ONLY, SESSION_MAX_AGE, SESSION_SAME_SITE
from app.services.setting import get_password_min_length


def test_engine_kwargs_adds_sqlite_connect_args() -> None:
    assert _engine_kwargs("sqlite:///./sales.db") == {
        "connect_args": {"check_same_thread": False}
    }


def test_engine_kwargs_skips_sqlite_only_args_for_other_backends() -> None:
    assert _engine_kwargs("postgresql://user:pass@localhost/db") == {}


def test_session_defaults_are_exposed() -> None:
    assert SESSION_COOKIE_NAME
    assert SESSION_SAME_SITE in {"lax", "strict", "none"}
    assert SESSION_MAX_AGE > 0
    assert isinstance(SESSION_HTTPS_ONLY, bool)
    assert PASSWORD_MIN_LENGTH >= 8


def test_password_min_length_setting_falls_back_to_config(db_session) -> None:
    assert get_password_min_length(db_session) == PASSWORD_MIN_LENGTH

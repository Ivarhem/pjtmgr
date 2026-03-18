from app.config import (
    DATABASE_URL,
    APP_PORT,
    ENABLED_MODULES,
    PASSWORD_MIN_LENGTH,
    SESSION_COOKIE_NAME,
    SESSION_HTTPS_ONLY,
    SESSION_MAX_AGE,
    SESSION_SAME_SITE,
    get_enabled_modules,
)
from app.services.setting import get_password_min_length


def test_database_url_defaults_to_postgresql() -> None:
    assert DATABASE_URL.startswith("postgresql://")


def test_app_port_default() -> None:
    assert APP_PORT == 9000


def test_enabled_modules_parsing() -> None:
    modules = get_enabled_modules()
    assert isinstance(modules, list)
    assert len(modules) > 0
    assert "common" in modules


def test_session_defaults_are_exposed() -> None:
    assert SESSION_COOKIE_NAME
    assert SESSION_SAME_SITE in {"lax", "strict", "none"}
    assert SESSION_MAX_AGE > 0
    assert isinstance(SESSION_HTTPS_ONLY, bool)
    assert PASSWORD_MIN_LENGTH >= 8


def test_password_min_length_setting_falls_back_to_config(db_session) -> None:
    assert get_password_min_length(db_session) == PASSWORD_MIN_LENGTH

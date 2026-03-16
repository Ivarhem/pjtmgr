from app.database import _engine_kwargs


def test_engine_kwargs_adds_sqlite_connect_args() -> None:
    assert _engine_kwargs("sqlite:///./sales.db") == {
        "connect_args": {"check_same_thread": False}
    }


def test_engine_kwargs_skips_sqlite_only_args_for_other_backends() -> None:
    assert _engine_kwargs("postgresql://user:pass@localhost/db") == {}

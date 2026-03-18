import pytest

from app.core.app_factory import create_app
from app.core.auth.middleware import AuthMiddleware
from app.core.exceptions import NotFoundError
from app.core.exceptions import UnauthorizedError
from app.modules.accounting.models.contract import Contract
from app.modules.common.models.user import User
from app.modules.common.routers import health as health_router
from app.modules.accounting.schemas.receipt import ReceiptCreate
from app.modules.accounting.services import contract as contract_service
from app.modules.accounting.services import receipt as receipt_service


def test_create_app_registers_core_routes() -> None:
    app = create_app()
    routes = {route.path for route in app.routes}

    assert "/api/v1/auth/login" in routes
    assert "/api/v1/dashboard/summary" in routes
    assert "/login" in routes
    assert any(m.cls.__name__ == "SessionMiddleware" for m in app.user_middleware)


def test_lifespan_uses_split_startup_steps(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("app.startup.lifespan.prepare_database", lambda: calls.append("db"))
    monkeypatch.setattr("app.startup.lifespan.initialize_reference_data", lambda: calls.append("bootstrap"))

    async def _run() -> None:
        app = create_app()
        async with app.router.lifespan_context(app):
            pass

    import asyncio

    asyncio.run(_run())
    assert calls == ["db", "bootstrap"]


def test_prepare_database_runs_upgrade_for_fresh_db(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class _Inspector:
        @staticmethod
        def get_table_names() -> list[str]:
            return []

    monkeypatch.setattr("app.startup.database_init.inspect", lambda _engine: _Inspector())
    monkeypatch.setattr("app.startup.database_init.ENV", "production")
    monkeypatch.setattr(
        "app.startup.database_init.Base.metadata.create_all",
        lambda **_kwargs: calls.append(("create_all", "")),
    )
    monkeypatch.setattr("alembic.command.upgrade", lambda _cfg, rev: calls.append(("upgrade", rev)))
    monkeypatch.setattr("alembic.command.stamp", lambda _cfg, rev: calls.append(("stamp", rev)))

    from app.core.startup.database_init import prepare_database

    prepare_database()

    assert ("create_all", "") not in calls
    assert ("upgrade", "head") in calls
    assert all(name != "stamp" for name, _ in calls)


def test_auth_middleware_raises_standard_unauthorized_for_api() -> None:
    class _Request:
        class _Url:
            path = "/api/v1/contracts/1"

        url = _Url()
        session: dict[str, int] = {}

    async def _call() -> None:
        middleware = AuthMiddleware(app=lambda scope, receive, send: None)
        await middleware.dispatch(_Request(), lambda _request: None)

    import asyncio

    with pytest.raises(UnauthorizedError, match="로그인이 필요합니다."):
        asyncio.run(_call())


def test_health_check_hides_internal_error_details(monkeypatch) -> None:
    class _BrokenSession:
        @staticmethod
        def execute(_query):
            raise RuntimeError("db exploded")

    response = health_router.health_check(_BrokenSession())

    assert response == {"status": "degraded", "db": "unavailable"}


def test_contract_service_checks_access_in_service_layer(db_session) -> None:
    owner = User(name="담당자", login_id="owner", role="user")
    outsider = User(name="외부자", login_id="outsider", role="user")
    contract = Contract(contract_name="테스트 사업", contract_type="MA", owner=owner, status="active")
    db_session.add_all([owner, outsider, contract])
    db_session.commit()

    with pytest.raises(NotFoundError):
        contract_service.get_contract(db_session, contract.id, current_user=outsider)


def test_receipt_service_checks_access_in_service_layer(db_session) -> None:
    owner = User(name="담당자", login_id="owner", role="user")
    outsider = User(name="외부자", login_id="outsider", role="user")
    contract = Contract(contract_name="테스트 사업", contract_type="MA", owner=owner, status="active")
    db_session.add_all([owner, outsider, contract])
    db_session.commit()

    with pytest.raises(NotFoundError):
        receipt_service.create_receipt(
            db_session,
            contract.id,
            ReceiptCreate(
                customer_id=None,
                receipt_date="2026-03-01",
                revenue_month="2026-03-01",
                amount=1000,
                description="입금",
            ),
            current_user=outsider,
        )

from app.app_factory import create_app


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

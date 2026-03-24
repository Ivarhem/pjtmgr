"""Module registration tests: verify dynamic router registration based on ENABLED_MODULES.

These tests verify that the app factory correctly includes/excludes routers
depending on which modules are enabled. They use monkeypatch to override
the ENABLED_MODULES config without requiring a running database.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


def _get_route_paths(app) -> set[str]:
    """Extract all route paths from a FastAPI app."""
    return {route.path for route in app.routes if hasattr(route, "path")}


def _create_app_with_modules(enabled_modules: list[str]):
    """Create app with specific enabled modules, mocking DB-dependent startup."""
    with (
        patch("app.core.config.get_enabled_modules", return_value=enabled_modules),
        patch("app.core.config.ENABLED_MODULES", ",".join(enabled_modules)),
    ):
        from app.core.app_factory import create_app

        app = create_app()
    return app


# Accounting-specific route paths (a subset for checking)
_ACCOUNTING_ROUTES = {
    "/api/v1/dashboard/summary",
    "/api/v1/contracts",
    "/api/v1/reports/summary",
}

# Common route paths (always present when common is enabled)
_COMMON_ROUTES = {
    "/api/v1/partners",
    "/api/v1/users",
    "/api/v1/settings",
}

# Auth routes (always present)
_AUTH_ROUTES = {
    "/api/v1/auth/login",
    "/api/v1/auth/logout",
}

# Core page routes (always present)
_CORE_PAGE_ROUTES = {
    "/login",
    "/",
}

# Common page routes
_COMMON_PAGE_ROUTES = {
    "/partners",
    "/users",
    "/system",
    "/audit-logs",
}

# Accounting page routes
_ACCOUNTING_PAGE_ROUTES = {
    "/dashboard",
    "/my-contracts",
    "/contracts",
    "/reports",
}


class TestModuleRegistration:
    """Test dynamic module registration."""

    def test_common_and_accounting_enabled(self) -> None:
        """With common+accounting, accounting routes should exist."""
        app = _create_app_with_modules(["common", "accounting"])
        paths = _get_route_paths(app)

        # Auth routes always present
        for route in _AUTH_ROUTES:
            assert route in paths, f"Auth route {route} should always be present"

        # Core pages always present
        for route in _CORE_PAGE_ROUTES:
            assert route in paths, f"Core page route {route} should always be present"

        # Common routes present
        for route in _COMMON_ROUTES:
            assert route in paths, f"Common route {route} should be present"

        # Common pages present
        for route in _COMMON_PAGE_ROUTES:
            assert route in paths, f"Common page route {route} should be present"

        # Accounting routes present
        for route in _ACCOUNTING_ROUTES:
            assert route in paths, f"Accounting route {route} should be present"

        # Accounting pages present
        for route in _ACCOUNTING_PAGE_ROUTES:
            assert route in paths, f"Accounting page route {route} should be present"

    def test_common_only(self) -> None:
        """With only common, accounting routes should NOT exist."""
        app = _create_app_with_modules(["common"])
        paths = _get_route_paths(app)

        # Auth always present
        for route in _AUTH_ROUTES:
            assert route in paths, f"Auth route {route} should always be present"

        # Common routes present
        for route in _COMMON_ROUTES:
            assert route in paths, f"Common route {route} should be present"

        # Accounting routes should NOT be present
        for route in _ACCOUNTING_ROUTES:
            assert route not in paths, f"Accounting route {route} should NOT be present when accounting is disabled"

        # Accounting pages should NOT be present
        for route in _ACCOUNTING_PAGE_ROUTES:
            assert route not in paths, f"Accounting page route {route} should NOT be present when accounting is disabled"

    def test_all_modules_enabled(self) -> None:
        """With all modules enabled, all routes should exist."""
        app = _create_app_with_modules(["common", "accounting", "infra"])
        paths = _get_route_paths(app)

        # All common + accounting routes present
        for route in _AUTH_ROUTES | _COMMON_ROUTES | _ACCOUNTING_ROUTES:
            assert route in paths, f"Route {route} should be present with all modules enabled"

    def test_enabled_modules_in_jinja_globals(self) -> None:
        """enabled_modules should be set as a Jinja2 global variable."""
        app = _create_app_with_modules(["common", "accounting"])
        templates = app.state.templates
        assert "enabled_modules" in templates.env.globals
        assert "common" in templates.env.globals["enabled_modules"]
        assert "accounting" in templates.env.globals["enabled_modules"]

    def test_enabled_modules_without_accounting(self) -> None:
        """When accounting is disabled, it should not appear in Jinja2 globals."""
        app = _create_app_with_modules(["common"])
        templates = app.state.templates
        assert "accounting" not in templates.env.globals["enabled_modules"]

"""FastAPI application factory."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.auth.middleware import AuthMiddleware
from app.core.auth.router import router as auth_router
from app.core.config import (
    SESSION_COOKIE_NAME,
    SESSION_HTTPS_ONLY,
    SESSION_MAX_AGE,
    SESSION_SAME_SITE,
    SESSION_SECRET_KEY,
    get_enabled_modules,
)
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
    ValidationError,
)

# Always import all models for Alembic schema consistency
import app.modules.common.models  # noqa: F401
import app.modules.accounting.models  # noqa: F401
import app.modules.infra.models  # noqa: F401

from app.core.startup.lifespan import lifespan

_APP_ROOT = Path(__file__).resolve().parent.parent


class CacheControlStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        if scope.get("method") in {"GET", "HEAD"} and response.status_code == 200:
            # Static references include version query strings in templates. Cache them aggressively.
            response.headers.setdefault("Cache-Control", "public, max-age=31536000, immutable")
        return response



def create_app() -> FastAPI:
    root_path = os.getenv("APP_ROOT_PATH", "")
    app = FastAPI(title="사업관리 통합 플랫폼", lifespan=lifespan, root_path=root_path)
    app.mount("/static", CacheControlStaticFiles(directory="app/static"), name="static")

    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(ModuleContextMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key=SESSION_SECRET_KEY,
        session_cookie=SESSION_COOKIE_NAME,
        same_site=SESSION_SAME_SITE,
        https_only=SESSION_HTTPS_ONLY,
        max_age=SESSION_MAX_AGE,
    )

    register_exception_handlers(app)

    enabled = get_enabled_modules()
    register_routers(app, enabled)
    configure_templates(app, enabled)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(_request: Request, exc: UnauthorizedError):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(BusinessRuleError)
    async def business_rule_handler(_request: Request, exc: BusinessRuleError):
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.exception_handler(DuplicateError)
    async def duplicate_handler(_request: Request, exc: DuplicateError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(_request: Request, exc: PermissionDeniedError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_error_handler(_request: Request, exc: ValidationError):
        payload = {"detail": exc.errors}
        if exc.details:
            payload["error_details"] = exc.details
        return JSONResponse(status_code=422, content=payload)


def register_routers(app: FastAPI, enabled: list[str]) -> None:
    # Auth router is always registered
    app.include_router(auth_router)

    # Core pages (login, index, change-password) always registered
    from app.core import pages as core_pages

    app.include_router(core_pages.router)

    # Common module routers
    if "common" in enabled:
        from app.modules.common.routers import api_router as common_api_router

        app.include_router(common_api_router)

    # Accounting module routers
    if "accounting" in enabled:
        from app.modules.accounting.routers import api_router as accounting_api_router

        app.include_router(accounting_api_router)

    if "infra" in enabled:
        from app.modules.infra.routers import api_router as infra_api_router

        app.include_router(infra_api_router)


def configure_templates(app: FastAPI, enabled: list[str]) -> None:
    """Configure Jinja2 ChoiceLoader with template paths for active modules."""
    template_dirs: list[str] = []

    # Global templates (base.html, login.html, etc.) — highest priority
    global_templates = str(_APP_ROOT / "templates")
    if os.path.isdir(global_templates):
        template_dirs.append(global_templates)

    # Module template directories for active modules
    module_template_map = {
        "common": str(_APP_ROOT / "modules" / "common" / "templates"),
        "accounting": str(_APP_ROOT / "modules" / "accounting" / "templates"),
        "infra": str(_APP_ROOT / "modules" / "infra" / "templates"),
    }
    for module_name in enabled:
        tpl_dir = module_template_map.get(module_name)
        if tpl_dir and os.path.isdir(tpl_dir):
            template_dirs.append(tpl_dir)

    loader = ChoiceLoader([FileSystemLoader(d) for d in template_dirs])
    templates = Jinja2Templates(directory=template_dirs[0])
    templates.env.loader = loader

    # Inject enabled_modules as a Jinja2 global variable
    templates.env.globals["enabled_modules"] = enabled

    # Store templates on the app for access by page routers
    app.state.templates = templates


# ── Module context detection ──

_ACCOUNTING_PREFIXES = ("/my-contracts", "/contracts", "/dashboard", "/reports")
_INFRA_PREFIXES = (
    "/projects", "/periods", "/assets", "/asset-roles", "/ip-inventory", "/port-maps",
    "/physical-layout", "/product-catalog", "/catalog-integrity",
    "/policies", "/policy-definitions", "/contacts",
    "/audit-history", "/infra-dashboard",
    "/inventory/assets", "/infra-import",
)


def _detect_module(path: str) -> str | None:
    """Return 'accounting' or 'infra' if the path belongs to a module, else None."""
    for p in _ACCOUNTING_PREFIXES:
        if path.startswith(p):
            return "accounting"
    for p in _INFRA_PREFIXES:
        if path.startswith(p):
            return "infra"
    return None


class ModuleContextMiddleware:
    """Set request.state.module_context based on URL path + cookie fallback.

    Module-specific pages set the cookie to persist context across
    common pages (partners, audit-logs, users, etc.).
    """

    COOKIE_NAME = "module_context"

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path
        root_path = (scope.get("root_path") or "").rstrip("/")
        normalized_path = path
        if root_path and normalized_path.startswith(root_path):
            normalized_path = normalized_path[len(root_path):] or "/"
        detected = _detect_module(normalized_path)
        cookie_val = request.cookies.get(self.COOKIE_NAME)

        # Module page → use detected; common page → use cookie fallback
        module_ctx = detected or cookie_val or "accounting"
        scope.setdefault("state", {})["module_context"] = module_ctx

        # If the detected module changed, update cookie via response wrapper
        need_cookie = detected and detected != cookie_val

        if not need_cookie:
            await self.app(scope, receive, send)
            return

        # Wrap send to inject Set-Cookie header
        async def send_with_cookie(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                cookie_path = root_path or "/"
                cookie = (
                    f"{self.COOKIE_NAME}={detected}; Path={cookie_path}; "
                    "HttpOnly; SameSite=Lax; Max-Age=31536000"
                )
                headers.append((b"set-cookie", cookie.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_cookie)

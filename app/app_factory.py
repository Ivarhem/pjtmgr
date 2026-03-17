"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth.middleware import AuthMiddleware
from app.auth.router import router as auth_router
from app.config import (
    SESSION_COOKIE_NAME,
    SESSION_HTTPS_ONLY,
    SESSION_MAX_AGE,
    SESSION_SAME_SITE,
    SESSION_SECRET_KEY,
)
from app.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
    ValidationError,
)
from app.models import (  # noqa: F401 - 테이블 생성을 위해 모두 import
    AuditLog,
    Contract,
    ContractContact,
    ContractPeriod,
    ContractTypeConfig,
    Customer,
    CustomerContact,
    CustomerContactRole,
    LoginFailure,
    MonthlyForecast,
    Receipt,
    ReceiptMatch,
    Setting,
    TermConfig,
    TransactionLine,
    User,
    UserPreference,
)
from app.routers import (
    contract_contacts,
    contract_types,
    contracts,
    customers,
    dashboard,
    excel,
    forecasts,
    health,
    pages,
    receipt_matches,
    receipts,
    reports,
    settings,
    term_configs,
    transaction_lines,
    user_preferences,
    users,
)
from app.startup.lifespan import lifespan


def create_app() -> FastAPI:
    app = FastAPI(title="영업관리 시스템", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
    register_routers(app)
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


def register_routers(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(auth_router)
    app.include_router(dashboard.router)
    app.include_router(customers.router)
    app.include_router(contracts.router)
    app.include_router(transaction_lines.router)
    app.include_router(receipts.router)
    app.include_router(receipt_matches.router)
    app.include_router(forecasts.router)
    app.include_router(excel.router)
    app.include_router(users.router)
    app.include_router(settings.router)
    app.include_router(contract_contacts.router)
    app.include_router(contract_types.router)
    app.include_router(term_configs.router)
    app.include_router(user_preferences.router)
    app.include_router(reports.router)
    app.include_router(pages.router)

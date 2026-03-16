import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth.middleware import AuthMiddleware
from app.auth.router import router as auth_router
from app.config import (
    BOOTSTRAP_ADMIN_LOGIN_ID,
    BOOTSTRAP_ADMIN_NAME,
    BOOTSTRAP_ADMIN_PASSWORD,
    ENV,
    SESSION_SECRET_KEY,
)
from app.database import Base, engine
from app.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
    ValidationError,
)
from app.migrations_legacy import run_migrations
from app.models import (  # noqa: F401 - 테이블 생성을 위해 모두 import
    Contract,
    ContractContact,
    ContractPeriod,
    ContractTypeConfig,
    Customer,
    CustomerContact,
    CustomerContactRole,
    MonthlyForecast,
    Receipt,
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

# ── 로깅 설정 ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sales")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 생명주기 핸들러."""
    logger.info("영업관리 시스템 시작 (ENV=%s)", os.getenv("ENV", "dev"))
    # 개발 환경에서는 모델 스키마를 먼저 생성하되, 기존 데이터는 run_migrations()가 복구한다.
    if ENV == "dev":
        Base.metadata.create_all(bind=engine)
    run_migrations()
    # 시드 데이터 초기화
    from app.database import SessionLocal
    from app.services.contract_type_config import seed_defaults as seed_contract_types
    from app.services.term_config import seed_defaults as seed_terms
    from app.services.user import ensure_bootstrap_admin

    db = SessionLocal()
    try:
        seed_contract_types(db)
        seed_terms(db)
        admin = ensure_bootstrap_admin(
            db,
            login_id=BOOTSTRAP_ADMIN_LOGIN_ID,
            password=BOOTSTRAP_ADMIN_PASSWORD,
            name=BOOTSTRAP_ADMIN_NAME,
        )
        if admin:
            logger.info("초기 관리자 계정을 생성했습니다. login_id=%s", admin.login_id)
        elif ENV != "dev":
            logger.info("초기 관리자 bootstrap 미설정 상태로 시작했습니다.")
    finally:
        db.close()
    yield


app = FastAPI(title="영업관리 시스템", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# 미들웨어 등록 (순서 중요: Session → Auth)
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)


# ── 전역 예외 핸들러 ──────────────────────────────────────────
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
    return JSONResponse(status_code=422, content={"detail": exc.errors})


# ── 라우터 등록 ──────────────────────────────────────────────
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

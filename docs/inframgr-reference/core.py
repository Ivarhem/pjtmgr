# inframgr Auth + Core + Startup Reference
# Generated for migration reference - 2026-03-18

# ============================================
# FILE: app/main.py
# ============================================
from app.core.app_factory import create_app


app = create_app()


# ============================================
# FILE: app/app_factory.py
# ============================================
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
    ValidationError,
)
from app.core.auth.router import router as auth_router
from app.routers.asset_contacts import router as asset_contacts_router
from app.routers.asset_ips import router as asset_ips_router
from app.routers.assets import router as assets_router
from app.routers.ip_subnets import router as ip_subnets_router
from app.routers.contacts import router as contacts_router
from app.routers.pages import router as pages_router
from app.routers.partners import router as partners_router
from app.routers.policies import router as policies_router
from app.routers.policy_assignments import router as policy_assignments_router
from app.routers.port_maps import router as port_maps_router
from app.routers.project_deliverables import router as project_deliverables_router
from app.routers.project_phases import router as project_phases_router
from app.routers.projects import router as projects_router
from app.routers.sync import router as sync_router
from app.routers.users import router as users_router
from app.core.database import SessionLocal
from app.core.startup.bootstrap import bootstrap_admin
from app.core.startup.database_init import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    db = SessionLocal()
    try:
        bootstrap_admin(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)
    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(project_phases_router)
    app.include_router(project_deliverables_router)
    app.include_router(assets_router)
    app.include_router(ip_subnets_router)
    app.include_router(asset_ips_router)
    app.include_router(port_maps_router)
    app.include_router(partners_router)
    app.include_router(contacts_router)
    app.include_router(asset_contacts_router)
    app.include_router(policies_router)
    app.include_router(policy_assignments_router)
    app.include_router(users_router)
    app.include_router(sync_router)
    app.include_router(pages_router)

    @app.exception_handler(UnauthorizedError)
    async def handle_unauthorized(_, exc: UnauthorizedError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc) or "Unauthorized"})

    @app.exception_handler(PermissionDeniedError)
    async def handle_permission(_, exc: PermissionDeniedError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc) or "Permission denied"})

    @app.exception_handler(NotFoundError)
    async def handle_not_found(_, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc) or "Not found"})

    @app.exception_handler(DuplicateError)
    async def handle_duplicate(_, exc: DuplicateError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc) or "Duplicate resource"})

    @app.exception_handler(BusinessRuleError)
    async def handle_business(_, exc: BusinessRuleError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc) or "Validation error"})

    @app.exception_handler(ValidationError)
    async def handle_validation(_, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc) or "Validation error"})

    return app


# ============================================
# FILE: app/config.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "SI Project Inventory"
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./project_inventory.db")
    session_secret_key: str = os.getenv("SESSION_SECRET_KEY", "dev-session-secret")
    bootstrap_admin_login_id: str = os.getenv("BOOTSTRAP_ADMIN_LOGIN_ID", "admin")
    bootstrap_admin_password: str = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "admin")
    bootstrap_admin_name: str = os.getenv("BOOTSTRAP_ADMIN_NAME", "관리자")

    # External system integration (sales)
    sales_api_enabled: bool = os.getenv("SALES_API_ENABLED", "false").lower() == "true"
    sales_api_base_url: str = os.getenv("SALES_API_BASE_URL", "")
    sales_api_login_id: str = os.getenv("SALES_API_LOGIN_ID", "")
    sales_api_password: str = os.getenv("SALES_API_PASSWORD", "")


settings = Settings()

if settings.app_env != "development":
    if settings.session_secret_key == "dev-session-secret":
        raise RuntimeError("SESSION_SECRET_KEY must be set when APP_ENV is not 'development'.")
    if settings.database_url == "sqlite:///./project_inventory.db":
        raise RuntimeError("DATABASE_URL must be set when APP_ENV is not 'development'.")
    if settings.bootstrap_admin_password == "admin":
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD must be changed when APP_ENV is not 'development'.")


# ============================================
# FILE: app/database.py
# ============================================
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, future=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# FILE: app/exceptions.py
# ============================================
class AppError(Exception):
    """Base exception for application-level errors."""


class UnauthorizedError(AppError):
    pass


class PermissionDeniedError(AppError):
    pass


class NotFoundError(AppError):
    pass


class DuplicateError(AppError):
    pass


class BusinessRuleError(AppError):
    pass


class ValidationError(AppError):
    pass


# ============================================
# FILE: app/auth/__init__.py
# ============================================
"""Authentication and authorization helpers."""


# ============================================
# FILE: app/auth/authorization.py
# ============================================
from __future__ import annotations

from app.core.auth.constants import ROLE_ADMIN


def can_manage_users(user) -> bool:
    return getattr(user, "role", None) == ROLE_ADMIN


def can_manage_policies(user) -> bool:
    return getattr(user, "role", None) == ROLE_ADMIN


def can_edit_inventory(user) -> bool:
    return getattr(user, "role", None) in {ROLE_ADMIN, "user"}


# ============================================
# FILE: app/auth/constants.py
# ============================================
ROLE_ADMIN = "admin"
ROLE_USER = "user"


# ============================================
# FILE: app/auth/dependencies.py
# ============================================
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from app.core.auth.constants import ROLE_ADMIN
from app.core.exceptions import PermissionDeniedError, UnauthorizedError


@dataclass
class SessionUser:
    login_id: str
    name: str
    role: str


def get_current_user(request: Request) -> SessionUser:
    login_id = request.session.get("login_id")
    if not login_id:
        raise UnauthorizedError("Login required")
    return SessionUser(
        login_id=login_id,
        name=request.session.get("name", login_id),
        role=request.session.get("role", "user"),
    )


def require_admin(request: Request) -> SessionUser:
    user = get_current_user(request)
    if user.role != ROLE_ADMIN:
        raise PermissionDeniedError("Admin role required")
    return user


# ============================================
# FILE: app/auth/middleware.py
# ============================================
"""Reserved for custom authentication middleware when the project outgrows pure session use."""


# ============================================
# FILE: app/auth/password.py
# ============================================
from __future__ import annotations

import bcrypt


def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(raw_password.encode("utf-8"), hashed_password.encode("utf-8"))


# ============================================
# FILE: app/auth/router.py
# ============================================
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth.constants import ROLE_ADMIN
from app.core.auth.dependencies import get_current_user
from app.core.auth.service import authenticate
from app.core.database import get_db


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login_id: str
    password: str


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = authenticate(db, payload.login_id, payload.password)
    request.session.update(user)
    return user


@router.post("/logout")
def logout(request: Request) -> dict[str, str]:
    request.session.clear()
    return {"status": "ok"}


@router.get("/me")
def me(request: Request) -> dict[str, object]:
    user = get_current_user(request)
    return {
        "login_id": user.login_id,
        "name": user.name,
        "role": user.role,
        "permissions": {
            "can_manage_users": user.role == ROLE_ADMIN,
            "can_manage_policies": user.role == ROLE_ADMIN,
            "can_edit_inventory": True,
        },
    }


# ============================================
# FILE: app/auth/service.py
# ============================================
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.auth.password import verify_password
from app.core.exceptions import UnauthorizedError
from app.modules.common.services.user_service import get_user_by_login_id


def authenticate(db: Session, login_id: str, password: str) -> dict[str, str]:
    user = get_user_by_login_id(db, login_id)
    if user is None:
        raise UnauthorizedError("Invalid credentials")

    if not user.is_active:
        raise UnauthorizedError("Account is deactivated")

    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")

    return {
        "login_id": user.login_id,
        "name": user.name,
        "role": user.role,
    }


# ============================================
# FILE: app/startup/__init__.py
# ============================================
"""Startup helpers."""


# ============================================
# FILE: app/startup/bootstrap.py
# ============================================
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.common.services.user_service import ensure_bootstrap_admin


def bootstrap_admin(db: Session) -> None:
    """환경변수 기반 부트스트랩 관리자 계정을 DB에 생성한다.

    이미 해당 login_id의 사용자가 존재하면 아무 작업도 하지 않는다.
    """
    ensure_bootstrap_admin(
        db,
        login_id=settings.bootstrap_admin_login_id,
        password=settings.bootstrap_admin_password,
        name=settings.bootstrap_admin_name,
    )


# ============================================
# FILE: app/startup/database_init.py
# ============================================
from __future__ import annotations

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


def initialize_database() -> None:
    if settings.database_url.startswith("sqlite"):
        from app.core.base_model import Base
        Base.metadata.create_all(bind=engine)
    else:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))



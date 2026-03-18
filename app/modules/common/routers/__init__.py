"""Common module aggregated router package."""
from fastapi import APIRouter

from app.modules.common.routers.customers import router as customers_router
from app.modules.common.routers.health import router as health_router
from app.modules.common.routers.settings import router as settings_router
from app.modules.common.routers.term_configs import router as term_configs_router
from app.modules.common.routers.user_preferences import router as user_preferences_router
from app.modules.common.routers.users import router as users_router
from app.modules.common.routers.pages import router as pages_router
from app.modules.common.routers.roles import router as roles_router
from app.modules.common.routers.project_contract_links import router as project_contract_links_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(customers_router)
api_router.include_router(users_router)
api_router.include_router(settings_router)
api_router.include_router(term_configs_router)
api_router.include_router(user_preferences_router)
api_router.include_router(pages_router)
api_router.include_router(roles_router)
api_router.include_router(project_contract_links_router)

# Re-export individual routers for backward compatibility
from app.modules.common.routers import customers  # noqa: E402, F811
from app.modules.common.routers import health  # noqa: E402, F811
from app.modules.common.routers import settings  # noqa: E402, F811
from app.modules.common.routers import term_configs  # noqa: E402, F811
from app.modules.common.routers import user_preferences  # noqa: E402, F811
from app.modules.common.routers import users  # noqa: E402, F811
from app.modules.common.routers import roles  # noqa: E402, F811
from app.modules.common.routers import project_contract_links  # noqa: E402, F811

__all__ = [
    "api_router",
    "customers",
    "health",
    "project_contract_links",
    "roles",
    "settings",
    "term_configs",
    "user_preferences",
    "users",
]

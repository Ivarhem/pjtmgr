"""Common module aggregated router package."""
from fastapi import APIRouter

from app.modules.common.routers.contracts import router as contracts_router
from app.modules.common.routers.contract_types import router as contract_types_router
from app.modules.common.routers.asset_type_codes import router as asset_type_codes_router
from app.modules.common.routers.partners import router as partners_router
from app.modules.common.routers.health import router as health_router
from app.modules.common.routers.settings import router as settings_router
from app.modules.common.routers.term_configs import router as term_configs_router
from app.modules.common.routers.user_preferences import router as user_preferences_router
from app.modules.common.routers.users import router as users_router
from app.modules.common.routers.pages import router as pages_router
from app.modules.common.routers.roles import router as roles_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(partners_router)
api_router.include_router(users_router)
api_router.include_router(settings_router)
api_router.include_router(term_configs_router)
api_router.include_router(user_preferences_router)
api_router.include_router(pages_router)
api_router.include_router(roles_router)
api_router.include_router(contracts_router)
api_router.include_router(contract_types_router)
api_router.include_router(asset_type_codes_router)

# Re-export individual routers for backward compatibility
from app.modules.common.routers import contracts  # noqa: E402, F811
from app.modules.common.routers import contract_types  # noqa: E402, F811
from app.modules.common.routers import asset_type_codes  # noqa: E402, F811
from app.modules.common.routers import partners  # noqa: E402, F811
from app.modules.common.routers import health  # noqa: E402, F811
from app.modules.common.routers import settings  # noqa: E402, F811
from app.modules.common.routers import term_configs  # noqa: E402, F811
from app.modules.common.routers import user_preferences  # noqa: E402, F811
from app.modules.common.routers import users  # noqa: E402, F811
from app.modules.common.routers import roles  # noqa: E402, F811

__all__ = [
    "api_router",
    "asset_type_codes",
    "contract_types",
    "contracts",
    "partners",
    "health",
    "roles",
    "settings",
    "term_configs",
    "user_preferences",
    "users",
]

"""Infra module aggregated router package."""
from fastapi import APIRouter

from app.core.auth.dependencies import require_module_access
from app.modules.infra.routers.projects import router as projects_router
from app.modules.infra.routers.project_phases import router as project_phases_router
from app.modules.infra.routers.project_deliverables import (
    router as project_deliverables_router,
)
from app.modules.infra.routers.assets import router as assets_router
from app.modules.infra.routers.asset_ips import router as asset_ips_router
from app.modules.infra.routers.ip_subnets import router as ip_subnets_router
from app.modules.infra.routers.port_maps import router as port_maps_router
from app.modules.infra.routers.policies import router as policies_router
from app.modules.infra.routers.policy_assignments import (
    router as policy_assignments_router,
)
from app.modules.infra.routers.asset_contacts import router as asset_contacts_router
from app.modules.infra.routers.pages import router as pages_router

api_router = APIRouter(dependencies=[require_module_access("infra", "read")])
api_router.include_router(projects_router)
api_router.include_router(project_phases_router)
api_router.include_router(project_deliverables_router)
api_router.include_router(assets_router)
api_router.include_router(asset_ips_router)
api_router.include_router(ip_subnets_router)
api_router.include_router(port_maps_router)
api_router.include_router(policies_router)
api_router.include_router(policy_assignments_router)
api_router.include_router(asset_contacts_router)
api_router.include_router(pages_router)

__all__ = ["api_router"]

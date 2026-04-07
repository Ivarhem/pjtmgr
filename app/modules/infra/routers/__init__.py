"""Infra module aggregated router package."""
from fastapi import APIRouter

from app.core.auth.dependencies import require_module_access
from app.modules.infra.routers.period_phases import router as period_phases_router
from app.modules.infra.routers.period_deliverables import (
    router as period_deliverables_router,
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
from app.modules.infra.routers.asset_softwares import router as asset_software_router
from app.modules.infra.routers.period_assets import router as period_assets_router
from app.modules.infra.routers.asset_relations import router as asset_relations_router
from app.modules.infra.routers.period_partners import router as period_partners_router
from app.modules.infra.routers.period_partner_contacts import (
    router as period_partner_contacts_router,
)
from app.modules.infra.routers.infra_dashboard import router as infra_dashboard_router
from app.modules.infra.routers.product_catalogs import router as product_catalog_router
from app.modules.infra.routers.infra_excel import router as infra_excel_router
from app.modules.infra.routers.asset_aliases import router as asset_aliases_router
from app.modules.infra.routers.asset_events import router as asset_events_router
from app.modules.infra.routers.asset_related_partners import (
    router as asset_related_partners_router,
)
from app.modules.infra.routers.asset_roles import router as asset_roles_router
from app.modules.infra.routers.centers import router as centers_router
from app.modules.infra.routers.rooms import router as rooms_router
from app.modules.infra.routers.racks import router as racks_router
from app.modules.infra.routers.catalog_attributes import (
    router as catalog_attributes_router,
)
from app.modules.infra.routers.classification_layouts import (
    router as classification_layouts_router,
)
from app.modules.infra.routers.asset_interfaces import (
    router as asset_interfaces_router,
)
from app.modules.infra.routers.catalog_integrity import (
    router as catalog_integrity_router,
)
from app.modules.infra.routers.pages import router as pages_router

api_router = APIRouter(dependencies=[require_module_access("infra", "read")])
api_router.include_router(period_phases_router)
api_router.include_router(period_deliverables_router)
api_router.include_router(assets_router)
api_router.include_router(asset_ips_router)
api_router.include_router(ip_subnets_router)
api_router.include_router(port_maps_router)
api_router.include_router(policies_router)
api_router.include_router(policy_assignments_router)
api_router.include_router(asset_contacts_router)
api_router.include_router(asset_software_router)
api_router.include_router(period_assets_router)
api_router.include_router(asset_relations_router)
api_router.include_router(period_partners_router)
api_router.include_router(period_partner_contacts_router)
api_router.include_router(infra_dashboard_router)
api_router.include_router(product_catalog_router)
api_router.include_router(infra_excel_router)
api_router.include_router(asset_aliases_router)
api_router.include_router(asset_events_router)
api_router.include_router(asset_related_partners_router)
api_router.include_router(asset_roles_router)
api_router.include_router(centers_router)
api_router.include_router(rooms_router)
api_router.include_router(racks_router)
api_router.include_router(catalog_attributes_router)
api_router.include_router(classification_layouts_router)
api_router.include_router(asset_interfaces_router)
api_router.include_router(catalog_integrity_router)
api_router.include_router(pages_router)

__all__ = ["api_router"]

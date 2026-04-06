"""Infra module page routes (HTML template rendering)."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import get_enabled_modules

router = APIRouter(tags=["infra-pages"])


def _templates(request: Request):
    """Get the Jinja2Templates instance from app state."""
    return request.app.state.templates


@router.get("/periods", response_class=HTMLResponse)
def periods_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_projects.html", {"request": request}
    )


@router.get("/periods/{period_id}", response_class=HTMLResponse)
def period_detail_page(request: Request, period_id: int) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_project_detail.html", {
            "request": request,
            "project_id": period_id,
            "enabled_modules": get_enabled_modules(),
        }
    )


@router.get("/projects")
def projects_redirect(request: Request) -> RedirectResponse:
    """Legacy /projects URL redirects to /periods."""
    return RedirectResponse("/periods", status_code=301)


@router.get("/projects/{project_id}")
def project_detail_redirect(request: Request, project_id: int) -> RedirectResponse:
    """Legacy project detail redirects to period detail."""
    return RedirectResponse(f"/periods/{project_id}", status_code=301)


@router.get("/assets", response_class=HTMLResponse)
def assets_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_assets.html", {"request": request}
    )


@router.get("/asset-roles", response_class=HTMLResponse)
def asset_roles_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_asset_roles.html", {"request": request}
    )


@router.get("/ip-inventory", response_class=HTMLResponse)
def ip_inventory_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_ip_inventory.html", {"request": request}
    )


@router.get("/port-maps", response_class=HTMLResponse)
def port_maps_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_port_maps.html", {"request": request}
    )


@router.get("/physical-layout", response_class=HTMLResponse)
def physical_layout_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_physical_layout.html", {"request": request}
    )


## TODO: 정책 기능은 향후 재설계 후 구현 예정
## 페이지 라우트 제거됨 (/policies, /policy-definitions)
## API 라우터(policy_assignments, policies)는 유지


@router.get("/contacts", response_class=HTMLResponse)
def contacts_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_contacts.html", {"request": request}
    )


@router.get("/audit-history", response_class=HTMLResponse)
def audit_history_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_audit_history.html", {"request": request}
    )


@router.get("/infra-dashboard")
def infra_dashboard_page(request: Request) -> RedirectResponse:
    """Dashboard merged into /periods page."""
    return RedirectResponse("/periods", status_code=301)


@router.get("/inventory/assets")
def inventory_assets_page(request: Request) -> RedirectResponse:
    """Legacy inventory URL redirects to the unified assets workspace."""
    return RedirectResponse("/assets", status_code=301)


@router.get("/infra-import")
def infra_import_page(request: Request) -> RedirectResponse:
    """Legacy import page redirects to assets where import is available."""
    return RedirectResponse("/assets", status_code=301)

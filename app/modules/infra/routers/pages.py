"""Infra module page routes (HTML template rendering)."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["infra-pages"])


def _templates(request: Request):
    """Get the Jinja2Templates instance from app state."""
    return request.app.state.templates


@router.get("/projects", response_class=HTMLResponse)
def projects_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_projects.html", {"request": request}
    )


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def project_detail_page(request: Request, project_id: int) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_project_detail.html",
        {"request": request, "project_id": project_id},
    )


@router.get("/assets", response_class=HTMLResponse)
def assets_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_assets.html", {"request": request}
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


@router.get("/policies", response_class=HTMLResponse)
def policies_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_policies.html", {"request": request}
    )


@router.get("/infra-dashboard", response_class=HTMLResponse)
def infra_dashboard_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_dashboard.html", {"request": request}
    )

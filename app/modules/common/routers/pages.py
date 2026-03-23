"""Common module page routes (HTML template rendering)."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"])


def _templates(request: Request):
    """Get the Jinja2Templates instance from app state."""
    return request.app.state.templates


@router.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("customers.html", {"request": request})


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("users.html", {"request": request})


@router.get("/system", response_class=HTMLResponse)
def system_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("system.html", {"request": request})


@router.get("/product-catalog", response_class=HTMLResponse)
def product_catalog_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("product_catalog.html", {"request": request})


@router.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("audit_logs.html", {"request": request})

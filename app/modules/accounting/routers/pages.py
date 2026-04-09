"""Accounting module page routes (HTML template rendering)."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"])


def _templates(request: Request):
    """Get the Jinja2Templates instance from app state."""
    return request.app.state.templates


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("dashboard.html", {"request": request})


@router.get("/my-contracts", response_class=HTMLResponse)
def my_contracts_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("my_contracts.html", {"request": request})


@router.get("/contracts", response_class=HTMLResponse)
def contracts_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("contracts.html", {"request": request})


@router.get("/contracts/new/{contract_id}", response_class=HTMLResponse)
def contract_detail_new_page(request: Request, contract_id: int) -> HTMLResponse:
    """Period 없는 신규 Contract 상세 — contract_id 기반 진입."""
    return _templates(request).TemplateResponse(
        "contract_detail.html",
        {"request": request, "contract_period_id": 0, "contract_id": contract_id},
    )


@router.get("/contracts/{contract_period_id}", response_class=HTMLResponse)
def contract_detail_page(request: Request, contract_period_id: int) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "contract_detail.html",
        {"request": request, "contract_period_id": contract_period_id, "contract_id": 0},
    )


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("reports.html", {"request": request})

"""HTML 페이지 라우트 (템플릿 렌더링)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import DEFAULT_HOME
from app.database import get_db
from app.services.setting import get_password_min_length

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["pages"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return templates.TemplateResponse(
        "change_password.html",
        {"request": request, "min_password_length": get_password_min_length(db)},
    )


@router.get("/")
def index() -> RedirectResponse:
    return RedirectResponse(url=DEFAULT_HOME)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/my-contracts", response_class=HTMLResponse)
def my_contracts_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("my_contracts.html", {"request": request})


@router.get("/contracts", response_class=HTMLResponse)
def contracts_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("contracts.html", {"request": request})


@router.get("/contracts/new/{contract_id}", response_class=HTMLResponse)
def contract_detail_new_page(request: Request, contract_id: int) -> HTMLResponse:
    """Period 없는 신규 Contract 상세 — contract_id 기반 진입."""
    return templates.TemplateResponse(
        "contract_detail.html", {"request": request, "contract_period_id": 0, "contract_id": contract_id}
    )


@router.get("/contracts/{contract_period_id}", response_class=HTMLResponse)
def contract_detail_page(request: Request, contract_period_id: int) -> HTMLResponse:
    return templates.TemplateResponse(
        "contract_detail.html", {"request": request, "contract_period_id": contract_period_id, "contract_id": 0}
    )


@router.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("customers.html", {"request": request})


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("reports.html", {"request": request})


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("users.html", {"request": request})


@router.get("/system", response_class=HTMLResponse)
def system_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("system.html", {"request": request})


@router.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("audit_logs.html", {"request": request})

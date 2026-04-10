"""Core page routes — login, index, change-password."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_enabled_modules
from app.core.database import get_db
from app.modules.common.services.setting import get_password_min_length

router = APIRouter(tags=["pages"])


def _with_root_path(request: Request, path: str) -> str:
    root_path = (request.scope.get("root_path") or "").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{root_path}{path}" if root_path else path


def _templates(request: Request):
    """Get the Jinja2Templates instance from app state."""
    return request.app.state.templates


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("login.html", {"request": request})


@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "change_password.html",
        {"request": request, "min_password_length": get_password_min_length(db)},
    )


@router.get("/")
def index(request: Request) -> RedirectResponse:
    """Redirect to appropriate home page based on enabled modules."""
    enabled = get_enabled_modules()
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        return RedirectResponse(url=_with_root_path(request, "/login"))

    if "accounting" in enabled:
        return RedirectResponse(url=_with_root_path(request, "/my-contracts"))
    elif "infra" in enabled:
        return RedirectResponse(url=_with_root_path(request, "/projects"))
    else:
        return RedirectResponse(url=_with_root_path(request, "/login"))

"""Forecast(월별 Forecast + Forecast Sync) 라우터."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.authorization import check_contract_access, check_period_access
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.monthly_forecast import MonthlyForecastCreate, MonthlyForecastRead
from app.services import forecast_sync as sync_svc
from app.services import monthly_forecast as svc

router = APIRouter(prefix="/api/v1", tags=["forecasts"])


# ── Forecast CRUD ─────────────────────────────────────────────

@router.get(
    "/contract-periods/{period_id}/forecasts",
    response_model=list[MonthlyForecastRead],
)
def get_forecasts(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MonthlyForecastRead]:
    check_period_access(db, period_id, current_user)
    return svc.get_forecasts(db, period_id)


@router.get("/contracts/{contract_id}/all-forecasts")
def list_all_forecasts(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    check_contract_access(db, contract_id, current_user)
    return svc.list_all_forecasts(db, contract_id)


@router.patch(
    "/contract-periods/{period_id}/forecasts",
    response_model=list[MonthlyForecastRead],
)
def upsert_forecasts(
    period_id: int,
    items: list[MonthlyForecastCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MonthlyForecastRead]:
    check_period_access(db, period_id, current_user)
    return svc.upsert_forecasts(db, period_id, items, created_by=current_user.id)


# ── Forecast → TransactionLine 동기화 ──────────────────────────

@router.get("/contracts/{contract_id}/forecast-sync-preview")
def preview_forecast_sync(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Forecast ↔ TransactionLine 대조 미리보기 (전체 period)."""
    check_contract_access(db, contract_id, current_user)
    return sync_svc.preview_forecast_sync(db, contract_id)


@router.post("/contracts/{contract_id}/forecast-sync", status_code=200)
def sync_transaction_lines_from_forecast(
    contract_id: int,
    body: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Forecast 기반 TransactionLine 동기화 (전체 period): 생성 + 선택 삭제."""
    check_contract_access(db, contract_id, current_user)
    delete_ids = (body or {}).get("delete_ids", [])
    return sync_svc.sync_transaction_lines_from_forecast(db, contract_id, delete_ids)

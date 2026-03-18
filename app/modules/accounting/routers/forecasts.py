"""Forecast(월별 Forecast + Forecast Sync) 라우터."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.accounting.schemas.monthly_forecast import MonthlyForecastCreate, MonthlyForecastRead
from app.modules.accounting.services import forecast_sync as sync_svc
from app.modules.accounting.services import monthly_forecast as svc

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
    return svc.get_forecasts(db, period_id, current_user=current_user)


@router.get("/contracts/{contract_id}/all-forecasts")
def list_all_forecasts(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return svc.list_all_forecasts(db, contract_id, current_user=current_user)


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
    return svc.upsert_forecasts(
        db,
        period_id,
        items,
        created_by=current_user.id,
        current_user=current_user,
    )


# ── Forecast → TransactionLine 동기화 ──────────────────────────

@router.get("/contracts/{contract_id}/forecast-sync-preview")
def preview_forecast_sync(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Forecast ↔ TransactionLine 대조 미리보기 (전체 period)."""
    return sync_svc.preview_forecast_sync(db, contract_id, current_user=current_user)


@router.post("/contracts/{contract_id}/forecast-sync", status_code=200)
def sync_transaction_lines_from_forecast(
    contract_id: int,
    body: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Forecast 기반 TransactionLine 동기화 (전체 period): 생성 + 선택 삭제."""
    delete_ids = (body or {}).get("delete_ids", [])
    return sync_svc.sync_transaction_lines_from_forecast(
        db,
        contract_id,
        delete_ids,
        current_user=current_user,
    )

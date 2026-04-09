"""MonthlyForecast(월별 Forecast) 서비스."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.auth.authorization import check_contract_access, check_period_access
from app.core.exceptions import BusinessRuleError
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.monthly_forecast import MonthlyForecast
from app.modules.common.models.user import User


def get_forecasts(
    db: Session,
    period_id: int,
    *,
    current_user: User | None = None,
) -> list[MonthlyForecast]:
    if current_user:
        check_period_access(db, period_id, current_user)
    return (
        db.query(MonthlyForecast)
        .filter(
            MonthlyForecast.contract_period_id == period_id,
            MonthlyForecast.is_current.is_(True),
        )
        .order_by(MonthlyForecast.forecast_month)
        .all()
    )


def list_all_forecasts(
    db: Session,
    contract_id: int,
    *,
    current_user: User | None = None,
) -> list[dict]:
    """Contract의 모든 Period에 대한 Forecast를 반환."""
    if current_user:
        check_contract_access(db, contract_id, current_user)
    period_ids = [
        p.id
        for p in db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id == contract_id)
        .order_by(ContractPeriod.period_year)
        .all()
    ]
    if not period_ids:
        return []
    rows = (
        db.query(MonthlyForecast)
        .filter(
            MonthlyForecast.contract_period_id.in_(period_ids),
            MonthlyForecast.is_current.is_(True),
        )
        .order_by(MonthlyForecast.forecast_month)
        .all()
    )
    return [
        {
            "contract_period_id": f.contract_period_id,
            "forecast_month": f.forecast_month,
            "revenue_amount": f.revenue_amount,
            "gp_amount": f.gp_amount,
        }
        for f in rows
    ]


def upsert_forecasts(
    db: Session,
    period_id: int,
    items: list,
    *,
    created_by: int | None = None,
    current_user: User | None = None,
) -> list[MonthlyForecast]:
    if current_user:
        check_period_access(db, period_id, current_user)
    period = db.get(ContractPeriod, period_id)
    if period and period.is_completed:
        raise BusinessRuleError("완료된 귀속기간의 Forecast는 수정할 수 없습니다.")
    existing = {
        f.forecast_month: f
        for f in db.query(MonthlyForecast)
        .filter(
            MonthlyForecast.contract_period_id == period_id,
            MonthlyForecast.is_current.is_(True),
        )
        .all()
    }
    incoming_months = set()
    for item in items:
        incoming_months.add(item.forecast_month)
        if item.forecast_month in existing:
            existing[item.forecast_month].revenue_amount = item.revenue_amount
            existing[item.forecast_month].gp_amount = item.gp_amount
        else:
            db.add(
                MonthlyForecast(
                    contract_period_id=period_id,
                    forecast_month=item.forecast_month,
                    revenue_amount=item.revenue_amount,
                    gp_amount=item.gp_amount,
                    created_by=created_by,
                )
            )
    # 전송 목록에 없는 기존 행 삭제
    for month, row in existing.items():
        if month not in incoming_months:
            db.delete(row)
    db.commit()
    return get_forecasts(db, period_id, current_user=current_user)

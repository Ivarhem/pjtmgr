"""Forecast → TransactionLine 동기화 서비스."""
from __future__ import annotations

import calendar
import datetime

from sqlalchemy.orm import Session

from app.core.auth.authorization import check_contract_access
from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.monthly_forecast import MonthlyForecast
from app.modules.accounting.models.transaction_line import STATUS_EXPECTED, TransactionLine
from app.modules.common.models.user import User
from app.modules.accounting.services.transaction_line import _transaction_line_dict


def _calc_invoice_date(src: ContractPeriod | Contract, revenue_month: str) -> str | None:
    """발행일 규칙에 따라 invoice_issue_date를 계산.

    src: ContractPeriod 또는 Contract (invoice_day_type 등 속성 보유 객체)
    revenue_month: "YYYY-MM-01" 형식
    반환: "YYYY-MM-DD" 또는 None (규칙 미설정 시)
    """
    from dateutil.relativedelta import relativedelta

    if not src.invoice_day_type:
        return None

    base = datetime.datetime.strptime(revenue_month, "%Y-%m-%d").date()

    # 월 오프셋 적용 (0=당월, 1=익월, ...)
    offset = src.invoice_month_offset or 0
    target = base + relativedelta(months=offset)

    # 일자 결정
    if src.invoice_day_type == "1일":
        day = 1
    elif src.invoice_day_type == "말일":
        day = calendar.monthrange(target.year, target.month)[1]
    elif src.invoice_day_type == "특정일" and src.invoice_day:
        last_day = calendar.monthrange(target.year, target.month)[1]
        day = min(src.invoice_day, last_day)
    else:
        return None

    return target.replace(day=day).strftime("%Y-%m-%d")


def _all_forecast_months(db: Session, contract_id: int) -> dict[str, dict]:
    """사업의 전체 period에 걸친 forecast 월별 매출 합산.

    Returns:
        {month: {"amount": int, "period_id": int}} — period_id는 마지막으로 기여한 period
    """
    period_ids = [
        p.id
        for p in db.query(ContractPeriod.id)
        .filter(ContractPeriod.contract_id == contract_id)
        .all()
    ]
    if not period_ids:
        return {}
    forecasts = (
        db.query(MonthlyForecast)
        .filter(
            MonthlyForecast.contract_period_id.in_(period_ids),
            MonthlyForecast.is_current.is_(True),
        )
        .all()
    )
    result: dict[str, dict] = {}
    for f in forecasts:
        if f.revenue_amount:
            if f.forecast_month in result:
                result[f.forecast_month]["amount"] += f.revenue_amount
            else:
                result[f.forecast_month] = {
                    "amount": f.revenue_amount,
                    "period_id": f.contract_period_id,
                }
    return result


def preview_forecast_sync(
    db: Session,
    contract_id: int,
    *,
    current_user: User | None = None,
) -> dict:
    """Forecast ↔ TransactionLine 대조 미리보기 (전체 period 기준, DB 변경 없음)."""
    if current_user:
        check_contract_access(db, contract_id, current_user)
    forecast_months = _all_forecast_months(db, contract_id)

    transaction_lines = (
        db.query(TransactionLine)
        .filter(
            TransactionLine.contract_id == contract_id,
            TransactionLine.line_type == "revenue",
        )
        .all()
    )
    tl_by_month: dict[str, list] = {}
    for a in transaction_lines:
        tl_by_month.setdefault(a.revenue_month, []).append(a)

    to_create = []
    for month, info in sorted(forecast_months.items()):
        if month not in tl_by_month:
            to_create.append({"revenue_month": month, "amount": info["amount"]})

    to_delete = []
    for month, rows in sorted(tl_by_month.items()):
        if month not in forecast_months:
            for a in rows:
                if a.status == STATUS_EXPECTED and a.customer_id is None:
                    to_delete.append(
                        {
                            "id": a.id,
                            "revenue_month": a.revenue_month,
                            "amount": a.supply_amount,
                        }
                    )

    return {"to_create": to_create, "to_delete": to_delete}


def sync_transaction_lines_from_forecast(
    db: Session,
    contract_id: int,
    delete_ids: list[int],
    *,
    current_user: User | None = None,
) -> dict:
    """Forecast 기반 TransactionLine 동기화 (전체 period): 생성 + 선택된 행 삭제."""
    if current_user:
        check_contract_access(db, contract_id, current_user)
    contract = db.get(Contract, contract_id)
    if not contract:
        return {"created": 0, "deleted": 0}

    # 삭제 (예정 상태만 삭제 가능)
    deleted = 0
    if delete_ids:
        rows = (
            db.query(TransactionLine)
            .filter(
                TransactionLine.id.in_(delete_ids),
                TransactionLine.contract_id == contract_id,
                TransactionLine.line_type == "revenue",
                TransactionLine.status == STATUS_EXPECTED,
            )
            .all()
        )
        for row in rows:
            db.delete(row)
            deleted += 1

    # 생성 (전체 period forecast 기준)
    forecast_months = _all_forecast_months(db, contract_id)
    existing = {
        (a.revenue_month, a.line_type)
        for a in db.query(TransactionLine)
        .filter(TransactionLine.contract_id == contract_id)
        .all()
    }
    # Period별 정보 조회 (매출처 + 발행일 규칙 결정용)
    period_map: dict[int, ContractPeriod] = {
        p.id: p
        for p in db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id == contract_id)
        .all()
    }
    created = []
    for month, info in sorted(forecast_months.items()):
        if (month, "revenue") not in existing:
            period = period_map.get(info["period_id"])
            # Period의 매출처 우선, 없으면 Contract의 end_customer fallback
            period_cust = period.customer_id if period else None
            customer_id = (
                period_cust if period_cust is not None else contract.end_customer_id
            )
            # 발행일: Period 설정 우선, 없으면 Contract fallback
            invoice_src = period if (period and period.invoice_day_type) else contract
            row = TransactionLine(
                contract_id=contract_id,
                revenue_month=month,
                line_type="revenue",
                customer_id=customer_id,
                supply_amount=info["amount"],
                invoice_issue_date=_calc_invoice_date(invoice_src, month),
                status=STATUS_EXPECTED,
            )
            db.add(row)
            created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)
    return {
        "created": len(created),
        "deleted": deleted,
        "rows": [_transaction_line_dict(r) for r in created],
    }

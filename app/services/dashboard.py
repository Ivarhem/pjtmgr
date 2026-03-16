"""대시보드 서비스.

metrics.py의 공통 집계 함수를 조합하여 대시보드 데이터를 구성한다.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_period import ContractPeriod
from app.models.transaction_line import STATUS_CONFIRMED, TransactionLine
from app.schemas.report import (
    ReportFilter,
    TargetVsActualResponse,
    TargetVsActualRow,
    TargetVsActualTotals,
)
from app.services.metrics import (
    aggregate_by_field,
    aggregate_monthly_trend,
    aggregate_totals,
    ar_warnings,
    build_filter,
    load_actuals,
    load_allocated_totals,
    load_filtered_periods,
    load_forecasts,
    load_payments,
    month_range,
    safe_pct,
    top_customers,
)

if TYPE_CHECKING:
    from app.models.user import User


def _default_date_from() -> str:
    return f"{datetime.date.today().year}-01"


def _default_date_to() -> str:
    return f"{datetime.date.today().year}-12"


_NUMERIC_FIELDS = (
    "forecast_revenue", "planned_forecast", "unplanned_forecast",
    "actual_revenue", "cost", "gp", "receipt", "ar",
)


def _regroup_trend(monthly_rows: list[dict], group_by: str) -> list[dict]:
    """월별 추이 데이터를 분기/반기/연 단위로 재집계."""
    if group_by == "quarter":
        label_fn = _quarter_label
    elif group_by == "half":
        label_fn = _half_label
    else:
        label_fn = _year_label

    buckets: dict[str, dict] = {}
    ordered: list[str] = []

    for row in monthly_rows:
        m = row["month"] + "-01"  # YYYY-MM → YYYY-MM-01
        lbl = label_fn(m)
        if lbl not in buckets:
            buckets[lbl] = {f: 0 for f in _NUMERIC_FIELDS}
            buckets[lbl]["month"] = lbl
            ordered.append(lbl)
        for f in _NUMERIC_FIELDS:
            buckets[lbl][f] += row.get(f, 0)

    result: list[dict] = []
    for lbl in ordered:
        b = buckets[lbl]
        b["gp_pct"] = safe_pct(b["gp"], b["actual_revenue"])
        result.append(b)
    return result


def get_dashboard(
    db: Session,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    owner_id: list[int] | None = None,
    department: list[str] | None = None,
    contract_type: list[str] | None = None,
    stage: list[str] | None = None,
    customer_id: list[int] | None = None,
    group_by: str = "month",
    current_user: User | None = None,
) -> dict:
    """대시보드 전체 데이터.

    Args:
        date_from: 시작월 (YYYY-MM). 미지정 시 올해 1월.
        date_to: 종료월 (YYYY-MM). 미지정 시 올해 12월.
        owner_id, department, contract_type, stage, customer_id: 선택적 필터.
        group_by: 집계 단위 (month/quarter/half/year).

    반환:
        kpis, trend, by_type, by_department, top_customers, ar_warnings
    """
    if group_by not in _VALID_GROUP_BY:
        group_by = "month"

    filt = build_filter(
        date_from or _default_date_from(),
        date_to or _default_date_to(),
        owner_id=owner_id,
        department=department,
        contract_type=contract_type,
        stage=stage,
        customer_id=customer_id,
    )

    label = f"{filt.date_from[:4]}"
    if filt.date_from[:4] != filt.date_to[:4]:
        label = f"{filt.date_from[:7]} ~ {filt.date_to[:7]}"

    kpis = aggregate_totals(db, filt, current_user)
    kpis.update(_compute_planned_metrics(db, filt, current_user))

    monthly_rows = aggregate_monthly_trend(db, filt, current_user)
    trend = _regroup_trend(monthly_rows, group_by) if group_by != "month" else monthly_rows

    return {
        "year": label,
        "kpis": kpis,
        "trend": trend,
        "group_by": group_by,
        "by_type": aggregate_by_field(db, filt, current_user, "contract_type"),
        "by_department": aggregate_by_field(db, filt, current_user, "department"),
        "top_customers": top_customers(db, filt, current_user, n=10),
        "ar_warnings": ar_warnings(db, filt, current_user, n=10),
    }


def _compute_planned_metrics(
    db: Session,
    filt: ReportFilter,
    current_user: User | None,
) -> dict:
    """KPI에 추가할 planned 기반 지표 계산.

    - target_revenue: 계획사업(is_planned=True) 기간의 Forecast 합계 (fallback: 균등분배)
    - planned_actual_revenue: 계획사업(is_planned=True) 기간의 확정 매출
    - unplanned_actual_revenue: 수시사업(is_planned=False) 기간의 확정 매출
    """
    periods = load_filtered_periods(db, filt, current_user)
    if not periods:
        return {
            "target_revenue": 0,
            "planned_actual_revenue": 0,
            "unplanned_actual_revenue": 0,
        }

    contract_ids = list({p.contract_id for p in periods})
    period_ids = [p.id for p in periods]

    fc_map = load_forecasts(db, period_ids, filt.date_from, filt.date_to)
    act_map = load_actuals(db, contract_ids, filt.date_from, filt.date_to)

    target_revenue = 0
    planned_actual = 0
    unplanned_actual = 0
    seen_actuals: set[tuple[int, str]] = set()

    for p in periods:
        if not (p.start_month and p.end_month):
            continue

        # target: planned 기간만
        if p.is_planned:
            fc_months = fc_map.get(p.id, {})
            if fc_months:
                for m, vals in fc_months.items():
                    if filt.date_from <= m <= filt.date_to:
                        target_revenue += vals.get("revenue", 0)
            else:
                # fallback: 균등분배
                p_months = month_range(p.start_month, p.end_month)
                if p_months:
                    share = p.expected_revenue_total // len(p_months)
                    remainder = p.expected_revenue_total - share * len(p_months)
                    for i, m in enumerate(p_months):
                        if filt.date_from <= m <= filt.date_to:
                            target_revenue += share + (remainder if i == 0 else 0)

        # actual: planned/unplanned 분류
        contract_months = act_map.get(p.contract_id, {})
        for m, vals in contract_months.items():
            if m < filt.date_from or m > filt.date_to:
                continue
            if m < p.start_month or m > p.end_month:
                continue
            key = (p.contract_id, m)
            if key in seen_actuals:
                continue
            seen_actuals.add(key)
            rev = vals.get("revenue", 0)
            if p.is_planned:
                planned_actual += rev
            else:
                unplanned_actual += rev

    return {
        "target_revenue": target_revenue,
        "planned_actual_revenue": planned_actual,
        "unplanned_actual_revenue": unplanned_actual,
    }


def get_my_contracts_summary(
    db: Session,
    current_user: User,
    *,
    period_year: list[int] | None = None,
    calendar_year: list[int] | None = None,
    active_month: str | None = None,
) -> dict:
    """현재 사용자의 사업 요약 통계.

    Returns:
        contract_count: 진행 중인 사업 수
        revenue_confirmed: 매출 확정 합계
        cost_confirmed: 매입 확정 합계
        gp: GP (매출 - 매입)
        gp_pct: GP% (GP / 매출 * 100)
        receipt_total: 입금 합계
        ar: 미수금 (매출 확정 - 입금)
        current_month_revenue: 이번 달 매출 확정
    """
    q = db.query(ContractPeriod.contract_id).join(ContractPeriod.contract)
    q = q.filter(
        or_(
            ContractPeriod.owner_user_id == current_user.id,
            and_(
                ContractPeriod.owner_user_id.is_(None),
                Contract.owner_user_id == current_user.id,
            ),
        )
    )
    if active_month:
        q = q.filter(
            ContractPeriod.start_month.isnot(None),
            ContractPeriod.end_month.isnot(None),
            ContractPeriod.start_month <= active_month,
            ContractPeriod.end_month >= active_month,
        )
    if period_year:
        q = q.filter(ContractPeriod.period_year.in_(period_year))
    if calendar_year:
        year_conditions = []
        for y in calendar_year:
            year_start = f"{y}-01-01"
            year_end = f"{y}-12-01"
            year_conditions.append(
                (ContractPeriod.start_month <= year_end)
                & (ContractPeriod.end_month >= year_start)
            )
        q = q.filter(or_(*year_conditions))
    contract_ids = [r[0] for r in q.distinct().all()]

    if not contract_ids:
        return {
            "contract_count": 0,
            "revenue_confirmed": 0,
            "cost_confirmed": 0,
            "gp": 0,
            "gp_pct": None,
            "receipt_total": 0,
            "ar": 0,
            "current_month_revenue": 0,
        }

    # 사업 수 (active 상태만)
    contract_count = (
        db.query(func.count(Contract.id))
        .filter(Contract.id.in_(contract_ids), Contract.status == "active")
        .scalar()
    )

    # 매출/매입 확정 합계
    def _sum_transaction_lines(line_type: str) -> int:
        val = (
            db.query(func.coalesce(func.sum(TransactionLine.supply_amount), 0))
            .filter(
                TransactionLine.contract_id.in_(contract_ids),
                TransactionLine.line_type == line_type,
                TransactionLine.status == STATUS_CONFIRMED,
            )
            .scalar()
        )
        return int(val)

    revenue_confirmed = _sum_transaction_lines("revenue")
    cost_confirmed = _sum_transaction_lines("cost")
    gp = revenue_confirmed - cost_confirmed
    gp_pct = (
        round(gp / revenue_confirmed * 100, 1) if revenue_confirmed > 0 else None
    )

    current_years = sorted(set(period_year or []) | set(calendar_year or []))
    if current_years:
        date_from = f"{min(current_years)}-01-01"
        date_to = f"{max(current_years)}-12-01"
    else:
        years = [
            row[0]
            for row in db.query(ContractPeriod.period_year)
            .filter(ContractPeriod.contract_id.in_(contract_ids))
            .distinct()
            .all()
        ]
        if years:
            date_from = f"{min(years)}-01-01"
            date_to = f"{max(years)}-12-01"
        else:
            today = datetime.date.today()
            date_from = f"{today.year}-01-01"
            date_to = f"{today.year}-12-01"

    act_map = load_actuals(db, contract_ids, date_from, date_to)
    pay_map = load_payments(db, contract_ids, date_from, date_to)
    alloc_map = load_allocated_totals(db, contract_ids, date_from, date_to)

    payment_total = sum(pay_map.get(did, 0) for did in contract_ids)
    total_revenue = sum(
        sum(v["revenue"] for v in act_map.get(did, {}).values())
        for did in contract_ids
    )
    total_allocated = sum(alloc_map.get(did, 0) for did in contract_ids)
    ar = total_revenue - total_allocated

    # 이번 달 매출
    today = datetime.date.today()
    current_month = f"{today.year}-{str(today.month).zfill(2)}-01"
    current_month_revenue = int(
        db.query(func.coalesce(func.sum(TransactionLine.supply_amount), 0))
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.line_type == "revenue",
            TransactionLine.status == STATUS_CONFIRMED,
            TransactionLine.revenue_month == current_month,
        )
        .scalar()
    )

    return {
        "contract_count": contract_count,
        "revenue_confirmed": revenue_confirmed,
        "cost_confirmed": cost_confirmed,
        "gp": gp,
        "gp_pct": gp_pct,
        "receipt_total": payment_total,
        "ar": ar,
        "current_month_revenue": current_month_revenue,
    }


# ── 매출 목표 vs 실적 ─────────────────────────────────────────

_VALID_GROUP_BY = {"month", "quarter", "half", "year"}


def _month_label(month: str) -> str:
    return month[:7]


def _quarter_label(month: str) -> str:
    m = int(month[5:7])
    return f"Q{(m - 1) // 3 + 1}"


def _half_label(month: str) -> str:
    m = int(month[5:7])
    return "H1" if m <= 6 else "H2"


def _year_label(month: str) -> str:
    return month[:4]


def get_target_vs_actual(
    db: Session,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    owner_id: list[int] | None = None,
    department: list[str] | None = None,
    contract_type: list[str] | None = None,
    customer_id: list[int] | None = None,
    group_by: str = "month",
    current_user: User | None = None,
) -> TargetVsActualResponse:
    """매출 목표 vs 실적 비교 대시보드."""
    if group_by not in _VALID_GROUP_BY:
        group_by = "month"

    filt = build_filter(
        date_from or _default_date_from(),
        date_to or _default_date_to(),
        owner_id=owner_id,
        department=department,
        contract_type=contract_type,
        customer_id=customer_id,
    )

    periods = load_filtered_periods(db, filt, current_user, with_owner=True)
    months = month_range(filt.date_from, filt.date_to)

    if group_by == "month":
        label_fn = _month_label
        ordered_labels = [m[:7] for m in months]
    elif group_by == "quarter":
        label_fn = _quarter_label
        ordered_labels = list(dict.fromkeys(_quarter_label(m) for m in months))
    elif group_by == "half":
        label_fn = _half_label
        ordered_labels = list(dict.fromkeys(_half_label(m) for m in months))
    else:  # year
        label_fn = _year_label
        ordered_labels = list(dict.fromkeys(_year_label(m) for m in months))

    if not periods:
        empty_rows = [
            TargetVsActualRow(label=lbl) for lbl in ordered_labels
        ]
        return TargetVsActualResponse(
            group_by=group_by,
            rows=empty_rows,
            totals=TargetVsActualTotals(),
        )

    contract_ids = list({p.contract_id for p in periods})
    period_ids = [p.id for p in periods]

    # 확정 매출 로딩 (contract 단위)
    act_map = load_actuals(db, contract_ids, filt.date_from, filt.date_to)

    # MonthlyForecast 로딩 (period 단위) — 목표 산출에 사용
    fc_map = load_forecasts(db, period_ids, filt.date_from, filt.date_to)

    # 그룹별 집계 버킷 초기화
    buckets: dict[str, dict] = {
        lbl: {
            "target_revenue": 0,
            "actual_revenue": 0,
            "planned_actual_revenue": 0,
            "unplanned_actual_revenue": 0,
            "lost_revenue": 0,
        }
        for lbl in ordered_labels
    }

    # 1) target_revenue, lost_revenue:
    #    MonthlyForecast 우선, 없으면 expected_revenue_total 균등분배 fallback
    for p in periods:
        if not (p.start_month and p.end_month):
            continue

        fc_months = fc_map.get(p.id, {})  # month → {"revenue": int, "gp": int}
        has_forecast = bool(fc_months)

        # fallback: 균등분배 계산 (Forecast 없는 월에 사용)
        p_months = month_range(p.start_month, p.end_month)
        if not p_months:
            continue
        monthly_share = p.expected_revenue_total // len(p_months) if p_months else 0
        remainder = p.expected_revenue_total - monthly_share * len(p_months)

        # 범위 내 월만 필터
        in_range = [m for m in p_months if filt.date_from <= m <= filt.date_to]
        if not in_range:
            continue

        for i, m in enumerate(in_range):
            lbl = label_fn(m)
            if lbl not in buckets:
                continue

            # 목표: Forecast 있으면 사용, 없으면 균등분배
            if has_forecast:
                target = fc_months.get(m, {}).get("revenue", 0)
            else:
                target = monthly_share + (remainder if i == 0 and m == p_months[0] else 0)

            if p.is_planned:
                buckets[lbl]["target_revenue"] += target
            if p.stage == "실주":
                buckets[lbl]["lost_revenue"] += target

    # 2) actual_revenue 분배 (contract 단위 → 월별)
    # period별로 해당 contract의 매출을 planned/unplanned로 분류
    # 한 contract가 planned+unplanned period를 동시에 가질 수 있으므로
    # contract의 실적은 해당 period의 start/end 범위 내 매출만 집계
    seen_actuals: set[tuple[int, str]] = set()  # (contract_id, month) 중복 방지

    for p in periods:
        if not (p.start_month and p.end_month):
            continue
        contract_months = act_map.get(p.contract_id, {})
        for m, vals in contract_months.items():
            if m < filt.date_from or m > filt.date_to:
                continue
            if m < p.start_month or m > p.end_month:
                continue

            lbl = label_fn(m)
            if lbl not in buckets:
                continue

            key = (p.contract_id, m)
            if key in seen_actuals:
                continue
            seen_actuals.add(key)

            rev = vals.get("revenue", 0)
            buckets[lbl]["actual_revenue"] += rev
            if p.is_planned:
                buckets[lbl]["planned_actual_revenue"] += rev
            else:
                buckets[lbl]["unplanned_actual_revenue"] += rev

    # 결과 조립
    rows: list[TargetVsActualRow] = []
    tot = TargetVsActualTotals()

    for lbl in ordered_labels:
        b = buckets[lbl]
        gap = b["target_revenue"] - b["actual_revenue"]
        row = TargetVsActualRow(
            label=lbl,
            target_revenue=b["target_revenue"],
            actual_revenue=b["actual_revenue"],
            planned_actual_revenue=b["planned_actual_revenue"],
            unplanned_actual_revenue=b["unplanned_actual_revenue"],
            lost_revenue=b["lost_revenue"],
            gap=gap,
            achievement_rate=safe_pct(b["actual_revenue"], b["target_revenue"]),
        )
        rows.append(row)

        tot.target_revenue += b["target_revenue"]
        tot.actual_revenue += b["actual_revenue"]
        tot.planned_actual_revenue += b["planned_actual_revenue"]
        tot.unplanned_actual_revenue += b["unplanned_actual_revenue"]
        tot.lost_revenue += b["lost_revenue"]

    tot.gap = tot.target_revenue - tot.actual_revenue
    tot.achievement_rate = safe_pct(tot.actual_revenue, tot.target_revenue)

    return TargetVsActualResponse(
        group_by=group_by,
        rows=rows,
        totals=tot,
    )

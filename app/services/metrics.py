"""공통 데이터 집계 엔진.

대시보드와 보고서가 공유하는 데이터 로딩·집계 함수를 제공한다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.contract import Contract
from app.models.contract_period import ContractPeriod
from app.models.monthly_forecast import MonthlyForecast
from app.models.transaction_line import TransactionLine, STATUS_CONFIRMED
from app.models.receipt import Receipt
from app.models.receipt_match import ReceiptMatch
from app.auth.authorization import apply_contract_scope
from app.schemas.report import ReportFilter
from app.models.customer import Customer

if TYPE_CHECKING:
    from app.models.user import User


# ── 필터·범위 유틸 ────────────────────────────────────────────────


def build_filter(
    date_from: str,
    date_to: str,
    *,
    owner_id: list[int] | None = None,
    department: list[str] | None = None,
    contract_type: list[str] | None = None,
    stage: list[str] | None = None,
    customer_id: list[int] | None = None,
) -> ReportFilter:
    """라우터 파라미터 → ReportFilter 변환."""
    df = date_from if len(date_from) > 7 else f"{date_from}-01"
    dt = date_to if len(date_to) > 7 else f"{date_to}-01"
    return ReportFilter(
        date_from=df,
        date_to=dt,
        owner_id=owner_id,
        department=department,
        contract_type=contract_type,
        stage=stage,
        customer_id=customer_id,
    )


def month_range(date_from: str, date_to: str) -> list[str]:
    """date_from ~ date_to 사이 모든 월을 YYYY-MM-01 리스트로 반환."""
    months: list[str] = []
    y1, m1 = int(date_from[:4]), int(date_from[5:7])
    y2, m2 = int(date_to[:4]), int(date_to[5:7])
    y, m = y1, m1
    while (y, m) <= (y2, m2):
        months.append(f"{y}-{m:02d}-01")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def years_in_range(date_from: str, date_to: str) -> list[int]:
    """날짜 범위에 포함된 연도 목록."""
    y1 = int(date_from[:4])
    y2 = int(date_to[:4])
    return list(range(y1, y2 + 1))


def safe_pct(numerator: int, denominator: int) -> float | None:
    """0 나누기 방지 퍼센트 계산."""
    return round(numerator / denominator * 100, 1) if denominator > 0 else None


# ── 쿼리 필터 ─────────────────────────────────────────────────────


def apply_common_filters(
    q,
    filt: ReportFilter,
    current_user: User | None,
) -> tuple:
    """ContractPeriod 쿼리에 공통 필터를 적용하고, 범위 내 연도 목록을 반환."""
    from app.models.user import User as UserModel

    years = years_in_range(filt.date_from, filt.date_to)
    # period_year가 범위 내이거나, start_month~end_month가 조회 기간과 겹치는 Period 포함
    q = q.filter(
        or_(
            ContractPeriod.period_year.in_(years),
            and_(
                ContractPeriod.start_month.isnot(None),
                ContractPeriod.end_month.isnot(None),
                ContractPeriod.start_month <= filt.date_to,
                ContractPeriod.end_month >= filt.date_from,
            ),
        )
    )

    if current_user:
        q = apply_contract_scope(q, current_user)
    if filt.owner_id:
        q = q.filter(
            or_(
                ContractPeriod.owner_user_id.in_(filt.owner_id),
                and_(
                    ContractPeriod.owner_user_id.is_(None),
                    Contract.owner_user_id.in_(filt.owner_id),
                ),
            )
        )
    if filt.department:
        q = q.filter(
            or_(
                ContractPeriod.owner.has(UserModel.department.in_(filt.department)),
                and_(
                    ContractPeriod.owner_user_id.is_(None),
                    Contract.owner.has(UserModel.department.in_(filt.department)),
                ),
            )
        )
    if filt.contract_type:
        q = q.filter(Contract.contract_type.in_(filt.contract_type))
    if filt.stage:
        q = q.filter(ContractPeriod.stage.in_(filt.stage))
    if filt.customer_id:
        q = q.filter(
            or_(
                ContractPeriod.customer_id.in_(filt.customer_id),
                Contract.end_customer_id.in_(filt.customer_id),
            )
        )

    return q, years


# ── 데이터 로딩 ───────────────────────────────────────────────────


def load_forecasts(
    db: Session, period_ids: list[int], date_from: str, date_to: str,
) -> dict[int, dict[str, dict]]:
    """period_id → month → {revenue, gp} 매핑."""
    if not period_ids:
        return {}
    rows = (
        db.query(
            MonthlyForecast.contract_period_id,
            MonthlyForecast.forecast_month,
            MonthlyForecast.revenue_amount,
            MonthlyForecast.gp_amount,
        )
        .filter(
            MonthlyForecast.contract_period_id.in_(period_ids),
            MonthlyForecast.is_current.is_(True),
            MonthlyForecast.forecast_month >= date_from,
            MonthlyForecast.forecast_month <= date_to,
        )
        .all()
    )
    result: dict[int, dict[str, dict]] = {}
    for pid, month, sales, gp in rows:
        result.setdefault(pid, {})[month] = {
            "revenue": sales or 0,
            "gp": gp or 0,
        }
    return result


def load_actuals(
    db: Session, contract_ids: list[int], date_from: str, date_to: str,
) -> dict[int, dict[str, dict]]:
    """contract_id → month → {revenue, cost} 매핑."""
    if not contract_ids:
        return {}
    rows = (
        db.query(
            TransactionLine.contract_id,
            TransactionLine.revenue_month,
            TransactionLine.line_type,
            func.sum(TransactionLine.supply_amount),
        )
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.status == STATUS_CONFIRMED,
            TransactionLine.revenue_month >= date_from,
            TransactionLine.revenue_month <= date_to,
        )
        .group_by(TransactionLine.contract_id, TransactionLine.revenue_month, TransactionLine.line_type)
        .all()
    )
    result: dict[int, dict[str, dict]] = {}
    for did, month, lt, total in rows:
        entry = result.setdefault(did, {}).setdefault(month, {"revenue": 0, "cost": 0})
        entry[lt] = int(total or 0)
    return result


def load_matched_totals(
    db: Session, contract_ids: list[int], date_from: str, date_to: str,
) -> dict[int, int]:
    """contract_id → 대사완료 합계 매핑."""
    if not contract_ids:
        return {}
    rows = (
        db.query(Receipt.contract_id, func.sum(ReceiptMatch.matched_amount))
        .join(ReceiptMatch, ReceiptMatch.receipt_id == Receipt.id)
        .join(TransactionLine, TransactionLine.id == ReceiptMatch.transaction_line_id)
        .filter(
            Receipt.contract_id.in_(contract_ids),
            TransactionLine.revenue_month >= date_from,
            TransactionLine.revenue_month <= date_to,
        )
        .group_by(Receipt.contract_id)
        .all()
    )
    return {did: int(total or 0) for did, total in rows}


def load_receipts(
    db: Session, contract_ids: list[int], date_from: str, date_to: str,
) -> dict[int, int]:
    """contract_id → total receipt 매핑."""
    if not contract_ids:
        return {}
    rows = (
        db.query(Receipt.contract_id, func.sum(Receipt.amount))
        .filter(
            Receipt.contract_id.in_(contract_ids),
            Receipt.revenue_month >= date_from,
            Receipt.revenue_month <= date_to,
        )
        .group_by(Receipt.contract_id)
        .all()
    )
    return {did: int(total or 0) for did, total in rows}


def load_matched_totals_monthly(
    db: Session, contract_ids: list[int], date_from: str, date_to: str,
) -> dict[int, dict[str, int]]:
    """contract_id → month → 대사완료 합계 매핑 (매출 귀속월 기준)."""
    if not contract_ids:
        return {}
    rows = (
        db.query(
            Receipt.contract_id,
            TransactionLine.revenue_month,
            func.sum(ReceiptMatch.matched_amount),
        )
        .join(ReceiptMatch, ReceiptMatch.receipt_id == Receipt.id)
        .join(TransactionLine, TransactionLine.id == ReceiptMatch.transaction_line_id)
        .filter(
            Receipt.contract_id.in_(contract_ids),
            TransactionLine.revenue_month >= date_from,
            TransactionLine.revenue_month <= date_to,
        )
        .group_by(Receipt.contract_id, TransactionLine.revenue_month)
        .all()
    )
    result: dict[int, dict[str, int]] = {}
    for did, month, total in rows:
        result.setdefault(did, {})[month] = int(total or 0)
    return result


def load_receipts_monthly(
    db: Session, contract_ids: list[int], date_from: str, date_to: str,
) -> dict[int, dict[str, int]]:
    """contract_id → month → receipt 매핑."""
    if not contract_ids:
        return {}
    rows = (
        db.query(
            Receipt.contract_id,
            Receipt.revenue_month,
            func.sum(Receipt.amount),
        )
        .filter(
            Receipt.contract_id.in_(contract_ids),
            Receipt.revenue_month >= date_from,
            Receipt.revenue_month <= date_to,
        )
        .group_by(Receipt.contract_id, Receipt.revenue_month)
        .all()
    )
    result: dict[int, dict[str, int]] = {}
    for did, month, total in rows:
        result.setdefault(did, {})[month] = int(total or 0)
    return result


# ── Backward compatibility aliases ──────────────────────────────
load_allocated_totals = load_matched_totals
load_payments = load_receipts


# ── 고수준 집계 (대시보드·보고서 공용) ────────────────────────────


def load_filtered_periods(
    db: Session,
    filt: ReportFilter,
    current_user: User | None,
    *,
    with_owner: bool = False,
    with_end_customer: bool = False,
) -> list[ContractPeriod]:
    """공통 필터 적용 후 ContractPeriod 목록 반환."""
    q = (
        db.query(ContractPeriod)
        .join(ContractPeriod.contract)
        .filter(Contract.status != "cancelled")
    )
    loads = [joinedload(ContractPeriod.contract)]
    if with_owner:
        loads.append(joinedload(ContractPeriod.contract).joinedload(Contract.owner))
        loads.append(joinedload(ContractPeriod.owner))
    if with_end_customer:
        loads.append(joinedload(ContractPeriod.contract).joinedload(Contract.end_customer))
    q = q.options(*loads)

    q, _ = apply_common_filters(q, filt, current_user)
    return q.all()


def _filtered_period_scope_subquery(db: Session, filt: ReportFilter, current_user: User | None):
    """집계용 filtered period scope 서브쿼리."""
    q = (
        db.query(
            ContractPeriod.id.label("period_id"),
            ContractPeriod.contract_id.label("contract_id"),
            ContractPeriod.is_planned.label("is_planned"),
        )
        .join(ContractPeriod.contract)
        .filter(Contract.status != "cancelled")
    )
    q, _ = apply_common_filters(q, filt, current_user)
    return q.subquery()


def _distinct_contract_ids_subquery(period_scope):
    return (
        period_scope.select()
        .with_only_columns(period_scope.c.contract_id)
        .distinct()
        .subquery()
    )


def aggregate_totals(
    db: Session,
    filt: ReportFilter,
    current_user: User | None,
) -> dict:
    """전체 KPI 합산: forecast_revenue, actual_revenue, cost, gp, gp_pct, receipt, ar, achievement_rate, contract_count."""
    period_scope = _filtered_period_scope_subquery(db, filt, current_user)
    contract_scope = _distinct_contract_ids_subquery(period_scope)

    contract_count = db.query(func.count()).select_from(contract_scope).scalar() or 0
    if contract_count == 0:
        return {
            "contract_count": 0,
            "forecast_revenue": 0, "actual_revenue": 0, "cost": 0,
            "gp": 0, "gp_pct": None, "receipt": 0, "ar": 0,
            "ar_rate": None, "achievement_rate": None,
        }

    total_fc = int(
        db.query(func.coalesce(func.sum(MonthlyForecast.revenue_amount), 0))
        .join(period_scope, MonthlyForecast.contract_period_id == period_scope.c.period_id)
        .filter(
            MonthlyForecast.is_current.is_(True),
            MonthlyForecast.forecast_month >= filt.date_from,
            MonthlyForecast.forecast_month <= filt.date_to,
        )
        .scalar()
        or 0
    )

    act_row = (
        db.query(
            func.coalesce(func.sum(case((TransactionLine.line_type == "revenue", TransactionLine.supply_amount), else_=0)), 0),
            func.coalesce(func.sum(case((TransactionLine.line_type == "cost", TransactionLine.supply_amount), else_=0)), 0),
        )
        .join(contract_scope, TransactionLine.contract_id == contract_scope.c.contract_id)
        .filter(
            TransactionLine.status == STATUS_CONFIRMED,
            TransactionLine.revenue_month >= filt.date_from,
            TransactionLine.revenue_month <= filt.date_to,
        )
        .one()
    )
    total_act_revenue = int(act_row[0] or 0)
    total_cost = int(act_row[1] or 0)

    gp = total_act_revenue - total_cost
    total_receipt = int(
        db.query(func.coalesce(func.sum(Receipt.amount), 0))
        .join(contract_scope, Receipt.contract_id == contract_scope.c.contract_id)
        .filter(
            Receipt.revenue_month >= filt.date_from,
            Receipt.revenue_month <= filt.date_to,
        )
        .scalar()
        or 0
    )
    total_allocated = int(
        db.query(func.coalesce(func.sum(ReceiptMatch.matched_amount), 0))
        .join(Receipt, Receipt.id == ReceiptMatch.receipt_id)
        .join(TransactionLine, TransactionLine.id == ReceiptMatch.transaction_line_id)
        .join(contract_scope, Receipt.contract_id == contract_scope.c.contract_id)
        .filter(
            TransactionLine.revenue_month >= filt.date_from,
            TransactionLine.revenue_month <= filt.date_to,
        )
        .scalar()
        or 0
    )
    ar = total_act_revenue - total_allocated

    return {
        "contract_count": int(contract_count),
        "forecast_revenue": total_fc,
        "actual_revenue": total_act_revenue,
        "cost": total_cost,
        "gp": gp,
        "gp_pct": safe_pct(gp, total_act_revenue),
        "receipt": total_receipt,
        "ar": ar,
        "ar_rate": safe_pct(ar, total_act_revenue),
        "achievement_rate": safe_pct(total_act_revenue, total_fc),
    }


def aggregate_monthly_trend(
    db: Session,
    filt: ReportFilter,
    current_user: User | None,
) -> list[dict]:
    """월별 추이: [{month, forecast_revenue, actual_revenue, cost, gp, gp_pct, receipt, ar}]."""
    period_scope = _filtered_period_scope_subquery(db, filt, current_user)
    months = month_range(filt.date_from, filt.date_to)

    if (db.query(func.count()).select_from(period_scope).scalar() or 0) == 0:
        return [
            {"month": m[:7], "forecast_revenue": 0, "planned_forecast": 0,
             "unplanned_forecast": 0, "actual_revenue": 0,
             "cost": 0, "gp": 0, "gp_pct": None, "receipt": 0, "ar": 0}
            for m in months
        ]

    contract_scope = _distinct_contract_ids_subquery(period_scope)

    fc_rows = (
        db.query(
            MonthlyForecast.forecast_month,
            func.coalesce(func.sum(MonthlyForecast.revenue_amount), 0),
            func.coalesce(
                func.sum(case((period_scope.c.is_planned.is_(True), MonthlyForecast.revenue_amount), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((period_scope.c.is_planned.is_(False), MonthlyForecast.revenue_amount), else_=0)),
                0,
            ),
        )
        .join(period_scope, MonthlyForecast.contract_period_id == period_scope.c.period_id)
        .filter(
            MonthlyForecast.is_current.is_(True),
            MonthlyForecast.forecast_month >= filt.date_from,
            MonthlyForecast.forecast_month <= filt.date_to,
        )
        .group_by(MonthlyForecast.forecast_month)
        .all()
    )
    fc_map = {
        month: {"forecast_revenue": int(total or 0), "planned_forecast": int(planned or 0), "unplanned_forecast": int(unplanned or 0)}
        for month, total, planned, unplanned in fc_rows
    }

    act_rows = (
        db.query(
            TransactionLine.revenue_month,
            func.coalesce(func.sum(case((TransactionLine.line_type == "revenue", TransactionLine.supply_amount), else_=0)), 0),
            func.coalesce(func.sum(case((TransactionLine.line_type == "cost", TransactionLine.supply_amount), else_=0)), 0),
        )
        .join(contract_scope, TransactionLine.contract_id == contract_scope.c.contract_id)
        .filter(
            TransactionLine.status == STATUS_CONFIRMED,
            TransactionLine.revenue_month >= filt.date_from,
            TransactionLine.revenue_month <= filt.date_to,
        )
        .group_by(TransactionLine.revenue_month)
        .all()
    )
    act_map = {month: {"revenue": int(revenue or 0), "cost": int(cost or 0)} for month, revenue, cost in act_rows}

    receipt_rows = (
        db.query(
            Receipt.revenue_month,
            func.coalesce(func.sum(Receipt.amount), 0),
        )
        .join(contract_scope, Receipt.contract_id == contract_scope.c.contract_id)
        .filter(
            Receipt.revenue_month >= filt.date_from,
            Receipt.revenue_month <= filt.date_to,
        )
        .group_by(Receipt.revenue_month)
        .all()
    )
    receipt_map = {month: int(total or 0) for month, total in receipt_rows}

    matched_rows = (
        db.query(
            TransactionLine.revenue_month,
            func.coalesce(func.sum(ReceiptMatch.matched_amount), 0),
        )
        .join(ReceiptMatch, ReceiptMatch.transaction_line_id == TransactionLine.id)
        .join(Receipt, Receipt.id == ReceiptMatch.receipt_id)
        .join(contract_scope, Receipt.contract_id == contract_scope.c.contract_id)
        .filter(
            TransactionLine.revenue_month >= filt.date_from,
            TransactionLine.revenue_month <= filt.date_to,
        )
        .group_by(TransactionLine.revenue_month)
        .all()
    )
    match_map = {month: int(total or 0) for month, total in matched_rows}

    rows: list[dict] = []
    for m in months:
        fc = fc_map.get(m, {})
        ac = act_map.get(m, {})
        fc_revenue = fc.get("forecast_revenue", 0)
        planned_fc = fc.get("planned_forecast", 0)
        unplanned_fc = fc.get("unplanned_forecast", 0)
        act_revenue = ac.get("revenue", 0)
        act_cost = ac.get("cost", 0)
        receipt = receipt_map.get(m, 0)
        allocated = match_map.get(m, 0)
        ar = act_revenue - allocated
        gp = act_revenue - act_cost

        rows.append({
            "month": m[:7],
            "forecast_revenue": fc_revenue,
            "planned_forecast": planned_fc,
            "unplanned_forecast": unplanned_fc,
            "actual_revenue": act_revenue,
            "cost": act_cost,
            "gp": gp,
            "gp_pct": safe_pct(gp, act_revenue),
            "receipt": receipt,
            "ar": ar,
        })

    return rows


def aggregate_by_field(
    db: Session,
    filt: ReportFilter,
    current_user: User | None,
    field: str,
) -> list[dict]:
    """contract_type 또는 department별 집계.

    field: "contract_type" | "department"
    반환: [{label, contract_count, forecast_revenue, actual_revenue, gp, gp_pct}]
    """
    periods = load_filtered_periods(db, filt, current_user, with_owner=True)
    if not periods:
        return []

    contract_ids = list({p.contract_id for p in periods})
    period_ids = [p.id for p in periods]

    fc_map = load_forecasts(db, period_ids, filt.date_from, filt.date_to)
    act_map = load_actuals(db, contract_ids, filt.date_from, filt.date_to)

    # group periods by field
    groups: dict[str, dict] = {}
    seen_contracts: dict[str, set[int]] = {}

    for p in periods:
        contract = p.contract
        if field == "contract_type":
            key = contract.contract_type or "(미지정)"
        elif field == "department":
            owner = p.owner or contract.owner
            key = (owner.department if owner else None) or "(미지정)"
        else:
            key = "(미지정)"

        if key not in groups:
            groups[key] = {"label": key, "contract_count": 0, "forecast_revenue": 0, "actual_revenue": 0, "cost": 0, "gp": 0}
            seen_contracts[key] = set()

        # forecast (period 단위)
        fc_months = fc_map.get(p.id, {})
        groups[key]["forecast_revenue"] += sum(v["revenue"] for v in fc_months.values())

        # actual/cost (contract 단위, 중복 방지)
        if contract.id not in seen_contracts[key]:
            seen_contracts[key].add(contract.id)
            groups[key]["contract_count"] += 1
            ac_months = act_map.get(contract.id, {})
            groups[key]["actual_revenue"] += sum(v["revenue"] for v in ac_months.values())
            groups[key]["cost"] += sum(v["cost"] for v in ac_months.values())

    result = []
    for g in groups.values():
        g["gp"] = g["actual_revenue"] - g["cost"]
        g["gp_pct"] = safe_pct(g["gp"], g["actual_revenue"])
        del g["cost"]
        result.append(g)

    result.sort(key=lambda r: r["actual_revenue"], reverse=True)
    return result


def top_customers(
    db: Session,
    filt: ReportFilter,
    current_user: User | None,
    n: int = 10,
) -> list[dict]:
    """매출 상위 N 거래처 (END 고객 기준).

    반환: [{customer_name, actual_revenue, contract_count}]
    """
    period_scope = _filtered_period_scope_subquery(db, filt, current_user)
    contract_scope = (
        db.query(
            period_scope.c.contract_id.label("contract_id"),
            Contract.end_customer_id.label("end_customer_id"),
        )
        .join(Contract, Contract.id == period_scope.c.contract_id)
        .distinct()
        .subquery()
    )

    if (db.query(func.count()).select_from(contract_scope).scalar() or 0) == 0:
        return []

    actuals_by_contract = (
        db.query(
            TransactionLine.contract_id.label("contract_id"),
            func.coalesce(func.sum(TransactionLine.supply_amount), 0).label("actual_revenue"),
        )
        .join(contract_scope, TransactionLine.contract_id == contract_scope.c.contract_id)
        .filter(
            TransactionLine.status == STATUS_CONFIRMED,
            TransactionLine.line_type == "revenue",
            TransactionLine.revenue_month >= filt.date_from,
            TransactionLine.revenue_month <= filt.date_to,
        )
        .group_by(TransactionLine.contract_id)
        .subquery()
    )

    rows = (
        db.query(
            func.coalesce(Customer.name, "(미지정)").label("customer_name"),
            func.coalesce(func.sum(func.coalesce(actuals_by_contract.c.actual_revenue, 0)), 0).label("actual_revenue"),
            func.count(func.distinct(contract_scope.c.contract_id)).label("contract_count"),
        )
        .outerjoin(Customer, Customer.id == contract_scope.c.end_customer_id)
        .outerjoin(actuals_by_contract, actuals_by_contract.c.contract_id == contract_scope.c.contract_id)
        .group_by(Customer.name)
        .order_by(func.coalesce(func.sum(func.coalesce(actuals_by_contract.c.actual_revenue, 0)), 0).desc())
        .limit(n)
        .all()
    )
    return [
        {
            "customer_name": customer_name,
            "actual_revenue": int(actual_revenue or 0),
            "contract_count": int(contract_count or 0),
        }
        for customer_name, actual_revenue, contract_count in rows
    ]


def ar_warnings(
    db: Session,
    filt: ReportFilter,
    current_user: User | None,
    n: int = 10,
) -> list[dict]:
    """미수금 상위 N건 경고.

    반환: [{contract_id, contract_name, owner_name, actual_revenue, receipt, ar, ar_rate}]
    """
    periods = load_filtered_periods(db, filt, current_user, with_owner=True)
    if not periods:
        return []

    contract_ids = list({p.contract_id for p in periods})
    act_map = load_actuals(db, contract_ids, filt.date_from, filt.date_to)
    rcpt_map = load_receipts(db, contract_ids, filt.date_from, filt.date_to)
    match_map = load_matched_totals(db, contract_ids, filt.date_from, filt.date_to)

    rows: list[dict] = []
    seen: set[int] = set()

    for p in periods:
        contract = p.contract
        if contract.id in seen:
            continue
        seen.add(contract.id)

        ac_months = act_map.get(contract.id, {})
        act_revenue = sum(v["revenue"] for v in ac_months.values())
        allocated = match_map.get(contract.id, 0)
        ar = act_revenue - allocated
        receipt = rcpt_map.get(contract.id, 0)

        if ar <= 0:
            continue

        rows.append({
            "contract_id": contract.id,
            "contract_name": contract.contract_name,
            "owner_name": p.owner.name if p.owner else contract.owner.name if contract.owner else None,
            "actual_revenue": act_revenue,
            "receipt": receipt,
            "ar": ar,
            "ar_rate": safe_pct(ar, act_revenue),
        })

    rows.sort(key=lambda r: r["ar"], reverse=True)
    return rows[:n]

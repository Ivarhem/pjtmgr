"""보고서 집계 서비스.

보고서 1: 요약 현황 (KPI + 월별 추이)
보고서 2: Forecast vs Actual (사업별 비교)
보고서 3: 미수 현황 (사업별 AR)
보고서 4: 매입매출관리 (사업별 거래처 피벗) — 기존 유지
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, and_
from sqlalchemy.orm import Session, joinedload

from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.monthly_forecast import MonthlyForecast
from app.modules.accounting.models.transaction_line import TransactionLine, STATUS_CONFIRMED
from app.modules.accounting.models.receipt import Receipt
from app.modules.accounting.models.receipt_match import ReceiptMatch
from app.core.exceptions import NotFoundError
from app.modules.accounting.schemas.report import ReportFilter
from app.modules.accounting.services.metrics import (
    build_filter as _build_filter,
    month_range as _month_range,
    years_in_range as _years_in_range,
    apply_common_filters as _apply_common_filters,
    load_forecasts as _load_forecasts,
    load_actuals as _load_actuals,
    load_matched_totals as _load_matched_totals,
    load_matched_totals_monthly as _load_matched_totals_monthly,
    load_receipts as _load_receipts,
    load_receipts_monthly as _load_receipts_monthly,
    safe_pct as _safe_pct,
)

if TYPE_CHECKING:
    from app.modules.common.models.user import User


# ═══ 보고서 1: 요약 현황 ═════════════════════════════════════════


def get_summary(
    db: Session,
    filt: ReportFilter,
    *,
    current_user: User | None = None,
) -> dict:
    """요약 현황: KPI + 월별 추이 테이블."""
    q = (
        db.query(ContractPeriod)
        .join(ContractPeriod.contract)
        .options(joinedload(ContractPeriod.contract), joinedload(ContractPeriod.owner))
        .filter(Contract.status != "cancelled")
    )
    q, years = _apply_common_filters(q, filt, current_user)
    periods = q.all()

    months = _month_range(filt.date_from, filt.date_to)

    if not periods:
        return {
            "kpis": {"forecast_revenue": 0, "actual_revenue": 0, "cost": 0, "gp": 0,
                     "gp_pct": None, "receipt": 0, "ar": 0, "achievement_rate": None},
            "period_summary": [
                {"month": m[:7], "forecast_revenue": 0, "actual_revenue": 0, "cost": 0,
                 "gp": 0, "gp_pct": None, "receipt": 0, "ar": 0}
                for m in months
            ],
        }

    contract_ids = list({p.contract_id for p in periods})
    period_ids = [p.id for p in periods]

    fc_map = _load_forecasts(db, period_ids, filt.date_from, filt.date_to)
    act_map = _load_actuals(db, contract_ids, filt.date_from, filt.date_to)
    rcpt_monthly_map = _load_receipts_monthly(db, contract_ids, filt.date_from, filt.date_to)
    match_monthly_map = _load_matched_totals_monthly(db, contract_ids, filt.date_from, filt.date_to)

    # period_id → contract_id 매핑
    contract_period_ids: dict[int, list[int]] = {}
    for p in periods:
        contract_period_ids.setdefault(p.contract_id, []).append(p.id)

    monthly_rows: list[dict] = []
    total_fc_revenue = 0
    total_act_revenue = 0
    total_cost = 0
    total_payment = 0

    for m in months:
        fc_revenue = 0
        for did, pids in contract_period_ids.items():
            for pid in pids:
                fc = fc_map.get(pid, {}).get(m)
                if fc:
                    fc_revenue += fc["revenue"]

        act_revenue = 0
        act_cost = 0
        for did in contract_ids:
            ac = act_map.get(did, {}).get(m)
            if ac:
                act_revenue += ac["revenue"]
                act_cost += ac["cost"]

        pay = sum(rcpt_monthly_map.get(did, {}).get(m, 0) for did in contract_ids)
        allocated = sum(match_monthly_map.get(did, {}).get(m, 0) for did in contract_ids)
        ar = act_revenue - allocated

        gp = act_revenue - act_cost
        total_fc_revenue += fc_revenue
        total_act_revenue += act_revenue
        total_cost += act_cost
        total_payment += pay

        monthly_rows.append({
            "month": m[:7],
            "forecast_revenue": fc_revenue,
            "actual_revenue": act_revenue,
            "cost": act_cost,
            "gp": gp,
            "gp_pct": _safe_pct(gp, act_revenue),
            "receipt": pay,
            "ar": ar,
        })

    total_gp = total_act_revenue - total_cost
    kpis = {
        "forecast_revenue": total_fc_revenue,
        "actual_revenue": total_act_revenue,
        "cost": total_cost,
        "gp": total_gp,
        "gp_pct": _safe_pct(total_gp, total_act_revenue),
        "receipt": total_payment,
        "ar": sum(row["ar"] for row in monthly_rows),
        "achievement_rate": _safe_pct(total_act_revenue, total_fc_revenue),
    }

    return {"kpis": kpis, "period_summary": monthly_rows}


# ═══ 보고서 2: Forecast vs Actual ════════════════════════════════


def list_forecast_vs_actual(
    db: Session,
    filt: ReportFilter,
    *,
    current_user: User | None = None,
) -> dict:
    """사업별 Forecast vs Actual 비교."""
    q = (
        db.query(ContractPeriod)
        .join(ContractPeriod.contract)
        .options(
            joinedload(ContractPeriod.contract).joinedload(Contract.end_partner),
            joinedload(ContractPeriod.contract).joinedload(Contract.owner),
            joinedload(ContractPeriod.owner),
        )
        .filter(Contract.status != "cancelled")
    )
    q, years = _apply_common_filters(q, filt, current_user)
    periods = q.order_by(Contract.contract_code).all()

    if not periods:
        return {"rows": [], "totals": None}

    contract_ids = list({p.contract_id for p in periods})
    period_ids = [p.id for p in periods]

    fc_map = _load_forecasts(db, period_ids, filt.date_from, filt.date_to)
    act_map = _load_actuals(db, contract_ids, filt.date_from, filt.date_to)

    # contract별 forecast 합산 (여러 period 가능)
    contract_fc: dict[int, int] = {}
    for p in periods:
        fc_months = fc_map.get(p.id, {})
        contract_fc[p.contract_id] = contract_fc.get(p.contract_id, 0) + sum(v["revenue"] for v in fc_months.values())

    rows: list[dict] = []
    seen_contracts: set[int] = set()
    total_fc = 0
    total_act_revenue = 0
    total_cost = 0

    for period in periods:
        contract = period.contract
        if contract.id in seen_contracts:
            continue
        seen_contracts.add(contract.id)
        owner = period.owner or contract.owner

        fc_revenue = contract_fc.get(contract.id, 0)
        ac_months = act_map.get(contract.id, {})
        act_revenue = sum(v["revenue"] for v in ac_months.values())
        act_cost = sum(v["cost"] for v in ac_months.values())

        gp = act_revenue - act_cost
        gap = fc_revenue - act_revenue

        total_fc += fc_revenue
        total_act_revenue += act_revenue
        total_cost += act_cost

        rows.append({
            "contract_id": contract.id,
            "contract_period_id": period.id,
            "contract_name": contract.contract_name,
            "contract_type": contract.contract_type,
            "owner_name": owner.name if owner else None,
            "department": owner.department if owner else None,
            "end_partner_name": contract.end_partner.name if contract.end_partner else None,
            "stage": period.stage,
            "forecast_revenue": fc_revenue,
            "actual_revenue": act_revenue,
            "gap_revenue": gap,
            "achievement_rate": _safe_pct(act_revenue, fc_revenue),
            "gp": gp,
            "gp_pct": _safe_pct(gp, act_revenue),
        })

    # gap 내림차순
    rows.sort(key=lambda r: r["gap_revenue"], reverse=True)

    total_gp = total_act_revenue - total_cost
    totals = {
        "contract_id": 0,
        "contract_period_id": 0,
        "contract_name": "합계",
        "contract_type": "",
        "owner_name": None,
        "department": None,
        "end_partner_name": None,
        "stage": None,
        "forecast_revenue": total_fc,
        "actual_revenue": total_act_revenue,
        "gap_revenue": total_fc - total_act_revenue,
        "achievement_rate": _safe_pct(total_act_revenue, total_fc),
        "gp": total_gp,
        "gp_pct": _safe_pct(total_gp, total_act_revenue),
    }

    return {"rows": rows, "totals": totals}


# ═══ 보고서 3: 미수 현황 ═════════════════════════════════════════


def list_receivables(
    db: Session,
    filt: ReportFilter,
    *,
    current_user: User | None = None,
) -> dict:
    """사업별 미수금 현황."""
    q = (
        db.query(ContractPeriod)
        .join(ContractPeriod.contract)
        .options(
            joinedload(ContractPeriod.contract).joinedload(Contract.end_partner),
            joinedload(ContractPeriod.contract).joinedload(Contract.owner),
            joinedload(ContractPeriod.owner),
        )
        .filter(Contract.status != "cancelled")
    )
    q, years = _apply_common_filters(q, filt, current_user)
    periods = q.order_by(Contract.contract_code).all()

    if not periods:
        return {
            "rows": [],
            "totals": {"actual_revenue": 0, "receipt": 0, "ar": 0, "ar_rate": None},
        }

    contract_ids = list({p.contract_id for p in periods})
    act_map = _load_actuals(db, contract_ids, filt.date_from, filt.date_to)
    rcpt_map = _load_receipts(db, contract_ids, filt.date_from, filt.date_to)
    match_map = _load_matched_totals(db, contract_ids, filt.date_from, filt.date_to)

    rows: list[dict] = []
    seen_contracts: set[int] = set()
    total_act_revenue = 0
    total_receipt = 0
    total_allocated = 0

    for period in periods:
        contract = period.contract
        if contract.id in seen_contracts:
            continue
        seen_contracts.add(contract.id)
        owner = period.owner or contract.owner

        ac_months = act_map.get(contract.id, {})
        act_revenue = sum(v["revenue"] for v in ac_months.values())
        receipt = rcpt_map.get(contract.id, 0)
        allocated = match_map.get(contract.id, 0)
        ar = act_revenue - allocated

        if ar <= 0 and act_revenue == 0:
            continue

        total_act_revenue += act_revenue
        total_receipt += receipt
        total_allocated += allocated

        rows.append({
            "contract_id": contract.id,
            "contract_name": contract.contract_name,
            "contract_type": contract.contract_type,
            "owner_name": owner.name if owner else None,
            "department": owner.department if owner else None,
            "end_partner_name": contract.end_partner.name if contract.end_partner else None,
            "actual_revenue": act_revenue,
            "receipt": receipt,
            "ar": ar,
            "ar_rate": _safe_pct(ar, act_revenue),
        })

    rows.sort(key=lambda r: r["ar"], reverse=True)

    total_ar = total_act_revenue - total_allocated
    return {
        "rows": rows,
        "totals": {
            "actual_revenue": total_act_revenue,
            "receipt": total_receipt,
            "ar": total_ar,
            "ar_rate": _safe_pct(total_ar, total_act_revenue),
        },
    }


# ═══ 보고서 4: 매입매출관리 (기존 유지) ══════════════════════════


def get_contract_pnl(
    db: Session,
    contract_id: int,
    period_year: int | None = None,
) -> dict:
    """사업별 매입매출관리: 거래처별 월별 매출/매입/입금 피벗 + GP + 미수금."""
    contract = db.query(Contract).options(
        joinedload(Contract.end_partner),
        joinedload(Contract.owner),
    ).filter(Contract.id == contract_id).first()
    if not contract:
        raise NotFoundError("사업을 찾을 수 없습니다.")

    if period_year:
        year_filter = f"{period_year}-%"
        years = [period_year]
    else:
        year_rows = (
            db.query(func.distinct(func.substr(TransactionLine.revenue_month, 1, 4)))
            .filter(TransactionLine.contract_id == contract_id)
            .all()
        )
        rcpt_years = (
            db.query(func.distinct(func.substr(Receipt.revenue_month, 1, 4)))
            .filter(Receipt.contract_id == contract_id)
            .all()
        )
        years = sorted({r[0] for r in year_rows} | {r[0] for r in rcpt_years if r[0]})
        if not years:
            years = [datetime.date.today().year]
        year_filter = None

    act_q = (
        db.query(TransactionLine)
        .options(joinedload(TransactionLine.partner))
        .filter(TransactionLine.contract_id == contract_id, TransactionLine.status == STATUS_CONFIRMED)
    )
    if year_filter:
        act_q = act_q.filter(TransactionLine.revenue_month.like(year_filter))
    transaction_lines = act_q.order_by(TransactionLine.revenue_month).all()

    rcpt_q = db.query(Receipt).options(joinedload(Receipt.partner)).filter(Receipt.contract_id == contract_id)
    if year_filter:
        rcpt_q = rcpt_q.filter(Receipt.revenue_month.like(year_filter))
    receipts = rcpt_q.order_by(Receipt.receipt_date).all()

    from app.modules.accounting.models.contract_contact import ContractContact
    from app.modules.accounting.models.contract_period import ContractPeriod as _DP
    from sqlalchemy.orm import joinedload as _jl
    period_ids = [p.id for p in db.query(_DP.id).filter(_DP.contract_id == contract_id).all()]
    contacts = (
        db.query(ContractContact)
        .options(_jl(ContractContact.partner_contact))
        .filter(ContractContact.contract_period_id.in_(period_ids))
        .all()
    ) if period_ids else []
    contact_map: dict[int, dict] = {}
    for c in contacts:
        cc = c.partner_contact
        if c.partner_id and c.partner_id not in contact_map and cc:
            contact_map[c.partner_id] = {
                "name": cc.name, "phone": cc.phone,
                "email": cc.email, "contact_type": c.contact_type,
            }

    active_months: set[str] = set()
    for a in transaction_lines:
        active_months.add(a.revenue_month)
    for p in receipts:
        if p.revenue_month:
            active_months.add(p.revenue_month)
    sorted_months = sorted(active_months)

    revenue_by_partner: dict[int | None, dict[str, int]] = {}
    cost_by_partner: dict[int | None, dict[str, int]] = {}

    for a in transaction_lines:
        cid = a.partner_id
        target = revenue_by_partner if a.line_type == "revenue" else cost_by_partner
        row = target.setdefault(cid, {})
        row[a.revenue_month] = row.get(a.revenue_month, 0) + (a.supply_amount or 0)

    receipt_by_partner: dict[int | None, dict[str, int]] = {}
    for p in receipts:
        cid = p.partner_id
        row = receipt_by_partner.setdefault(cid, {})
        month = p.revenue_month or "unknown"
        row[month] = row.get(month, 0) + (p.amount or 0)

    partner_names: dict[int | None, str] = {None: "(미지정)"}
    for a in transaction_lines:
        if a.partner_id and a.partner_id not in partner_names:
            partner_names[a.partner_id] = a.partner.name if a.partner else f"ID:{a.partner_id}"
    for p in receipts:
        if p.partner_id and p.partner_id not in partner_names:
            partner_names[p.partner_id] = p.partner.name if p.partner else f"ID:{p.partner_id}"

    def _build_rows(by_partner: dict, section: str) -> list[dict]:
        rows = []
        for cid, month_data in sorted(by_partner.items(), key=lambda x: partner_names.get(x[0], "")):
            contact = contact_map.get(cid, {})
            rows.append({
                "section": section,
                "partner_id": cid,
                "partner_name": partner_names.get(cid, "(미지정)"),
                "contact_name": contact.get("name"),
                "contact_phone": contact.get("phone"),
                "contact_email": contact.get("email"),
                "months": month_data,
                "total": sum(month_data.values()),
            })
        return rows

    revenue_rows = _build_rows(revenue_by_partner, "revenue")
    cost_rows = _build_rows(cost_by_partner, "cost")
    receipt_rows = _build_rows(receipt_by_partner, "receipt")

    revenue_totals: dict[str, int] = {}
    cost_totals: dict[str, int] = {}
    receipt_totals: dict[str, int] = {}
    matched_totals: dict[str, int] = {}

    for m in sorted_months:
        revenue_totals[m] = sum(r["months"].get(m, 0) for r in revenue_rows)
        cost_totals[m] = sum(r["months"].get(m, 0) for r in cost_rows)
        receipt_totals[m] = sum(r["months"].get(m, 0) for r in receipt_rows)

    matched_rows = (
        db.query(
            TransactionLine.revenue_month,
            func.sum(ReceiptMatch.matched_amount),
        )
        .join(ReceiptMatch, ReceiptMatch.transaction_line_id == TransactionLine.id)
        .join(Receipt, Receipt.id == ReceiptMatch.receipt_id)
        .filter(
            TransactionLine.contract_id == contract_id,
            Receipt.contract_id == contract_id,
            TransactionLine.status == STATUS_CONFIRMED,
        )
    )
    if year_filter:
        matched_rows = matched_rows.filter(TransactionLine.revenue_month.like(year_filter))
    for month, total in matched_rows.group_by(TransactionLine.revenue_month).all():
        matched_totals[month] = int(total or 0)
        if month not in revenue_totals and month not in cost_totals and month not in receipt_totals:
            sorted_months.append(month)

    sorted_months = sorted(set(sorted_months))

    gp_monthly: dict[str, int] = {}
    gp_pct_monthly: dict[str, float | None] = {}
    ar_monthly: dict[str, int] = {}
    cumulative_revenue = 0
    cumulative_matched = 0

    for m in sorted_months:
        s = revenue_totals.get(m, 0)
        c = cost_totals.get(m, 0)
        matched = matched_totals.get(m, 0)
        gp_monthly[m] = s - c
        gp_pct_monthly[m] = round((s - c) / s * 100, 1) if s > 0 else None
        cumulative_revenue += s
        cumulative_matched += matched
        ar_monthly[m] = cumulative_revenue - cumulative_matched

    grand_revenue = sum(revenue_totals.values())
    grand_cost = sum(cost_totals.values())
    grand_receipt = sum(receipt_totals.values())
    grand_matched = sum(matched_totals.values())

    return {
        "contract_id": contract.id,
        "contract_name": contract.contract_name,
        "contract_type": contract.contract_type,
        "end_partner_name": contract.end_partner.name if contract.end_partner else None,
        "owner_name": contract.owner.name if contract.owner else None,
        "years": [int(y) for y in years],
        "months": sorted_months,
        "revenue_rows": revenue_rows,
        "revenue_totals": revenue_totals,
        "cost_rows": cost_rows,
        "cost_totals": cost_totals,
        "gp_monthly": gp_monthly,
        "gp_pct_monthly": gp_pct_monthly,
        "receipt_rows": receipt_rows,
        "receipt_totals": receipt_totals,
        "ar_monthly": ar_monthly,
        "grand_revenue": grand_revenue,
        "grand_cost": grand_cost,
        "grand_gp": grand_revenue - grand_cost,
        "grand_gp_pct": round((grand_revenue - grand_cost) / grand_revenue * 100, 1) if grand_revenue > 0 else None,
        "grand_receipt": grand_receipt,
        "grand_ar": grand_revenue - grand_matched,
    }


# ═══ Excel Export (분리됨 → _report_export.py) ═════════════════
from app.modules.accounting.services._report_export import (  # noqa: E402
    export_summary,
    export_forecast_vs_actual,
    export_receivables,
    export_contract_pnl,
)

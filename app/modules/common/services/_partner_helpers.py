"""거래처 관련 사업·재무·입금 조회 헬퍼.

partner.py에서 분리된 교차 도메인 조회 함수들.
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.auth.authorization import has_full_contract_scope, list_accessible_contract_ids
from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.contract_contact import ContractContact
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.common.models.partner import Partner
from app.modules.accounting.models.receipt import Receipt
from app.modules.accounting.models.receipt_match import ReceiptMatch
from app.modules.accounting.models.transaction_line import TransactionLine
from app.core.exceptions import NotFoundError

if TYPE_CHECKING:
    from app.modules.common.models.user import User


def _related_contract_ids(db: Session, partner_id: int) -> set[int]:
    """거래처와 관련된 모든 사업 ID를 수집한다."""
    roles = _related_contract_roles(db, partner_id)
    result: set[int] = set()
    for ids in roles.values():
        result |= ids
    return result


def _related_contract_roles(db: Session, partner_id: int) -> dict[str, set[int]]:
    """거래처와 관련된 사업 ID를 역할별로 분류하여 반환한다."""
    end_cust_ids = {
        r[0] for r in db.query(Contract.id).filter(Contract.end_partner_id == partner_id).all()
    }
    period_cust_ids = {
        r[0]
        for r in db.query(ContractPeriod.contract_id)
        .filter(ContractPeriod.partner_id == partner_id)
        .distinct()
        .all()
    }
    contact_cust_ids = {
        r[0]
        for r in db.query(ContractPeriod.contract_id)
        .join(ContractContact, ContractContact.contract_period_id == ContractPeriod.id)
        .filter(ContractContact.partner_id == partner_id)
        .distinct()
        .all()
    }
    cost_cust_ids = {
        r[0]
        for r in db.query(TransactionLine.contract_id)
        .filter(TransactionLine.partner_id == partner_id, TransactionLine.line_type == "cost")
        .distinct()
        .all()
    }
    revenue_cust_ids = {
        r[0]
        for r in db.query(TransactionLine.contract_id)
        .filter(TransactionLine.partner_id == partner_id, TransactionLine.line_type == "revenue")
        .distinct()
        .all()
    }
    receipt_cust_ids = {
        r[0]
        for r in db.query(Receipt.contract_id).filter(Receipt.partner_id == partner_id).distinct().all()
    }
    return {
        "end_partner": end_cust_ids,
        "period_partner": period_cust_ids,
        "contact": contact_cust_ids,
        "cost": cost_cust_ids,
        "revenue": revenue_cust_ids,
        "receipt": receipt_cust_ids,
    }


def _build_period_lookup(db: Session, contract_ids: list[int]) -> list[ContractPeriod]:
    """관련 사업의 모든 period를 조회한다."""
    return (
        db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id.in_(contract_ids))
        .order_by(ContractPeriod.contract_id, ContractPeriod.period_year)
        .all()
    )


def _match_period(periods: list[ContractPeriod], contract_id: int, revenue_month: str) -> ContractPeriod | None:
    """revenue_month가 속하는 period를 찾는다 (start_month <= revenue_month <= end_month)."""
    for p in periods:
        if p.contract_id != contract_id:
            continue
        if p.start_month and p.end_month and p.start_month <= revenue_month <= p.end_month:
            return p
    # 범위 밖이면 가장 가까운 period 반환
    contract_periods = [p for p in periods if p.contract_id == contract_id]
    return contract_periods[-1] if contract_periods else None


def list_related_contracts(db: Session, partner_id: int, current_user: User | None = None) -> dict:
    """거래처와 관련된 사업 목록 (역할, 재무 요약 포함).

    Returns:
        {"summary": {active_count, completed_count, total_revenue}, "contracts": [...]}
    """
    _empty = {"summary": {"active_count": 0, "completed_count": 0, "total_revenue": 0}, "contracts": []}

    # ── 1) 관련 사업 ID 수집 + 역할별 분류 ──
    roles_map = _related_contract_roles(db, partner_id)
    end_cust_ids = roles_map["end_partner"]
    contract_ids: set[int] = set()
    for ids in roles_map.values():
        contract_ids |= ids
    if not contract_ids:
        return _empty

    if current_user and not has_full_contract_scope(current_user):
        visible_ids = set(list_accessible_contract_ids(db, current_user))
        contract_ids &= visible_ids
    if not contract_ids:
        return _empty

    # ── 2) 사업 조회 (Period 있는 활성 사업) ──
    contracts = (
        db.query(Contract)
        .options(joinedload(Contract.end_partner), joinedload(Contract.owner))
        .filter(
            Contract.id.in_(contract_ids),
            Contract.status != "cancelled",
            Contract.periods.any(),
        )
        .order_by(Contract.id.desc())
        .all()
    )
    if not contracts:
        return {"summary": {"active_count": 0, "completed_count": 0, "total_revenue": 0}, "contracts": []}

    active_contract_ids = [c.id for c in contracts]

    # ── 3) Period 조회 ──
    all_periods = (
        db.query(ContractPeriod)
        .filter(ContractPeriod.contract_id.in_(active_contract_ids))
        .order_by(ContractPeriod.contract_id.desc(), ContractPeriod.period_year.desc())
        .all()
    )
    contract_map: dict[int, Contract] = {c.id: c for c in contracts}

    # ── 4) Period 단위 매출/매입 벌크 집계 ──
    period_ids = [p.id for p in all_periods]
    fin_map: dict[int, dict[str, int]] = {}
    if period_ids:
        fin_rows = (
            db.query(
                ContractPeriod.id,
                TransactionLine.line_type,
                func.sum(TransactionLine.supply_amount),
            )
            .join(
                TransactionLine,
                TransactionLine.contract_id == ContractPeriod.contract_id,
            )
            .filter(
                ContractPeriod.id.in_(period_ids),
                TransactionLine.revenue_month >= ContractPeriod.start_month,
                TransactionLine.revenue_month <= ContractPeriod.end_month,
            )
            .group_by(ContractPeriod.id, TransactionLine.line_type)
            .all()
        )
        for pid, lt, total in fin_rows:
            fin_map.setdefault(pid, {"revenue": 0, "cost": 0})
            if lt == "revenue":
                fin_map[pid]["revenue"] = total or 0
            elif lt == "cost":
                fin_map[pid]["cost"] = total or 0

    # ── 5) Period 단위 역할 판별 ──
    period_revenue_set: set[int] = set()
    period_cost_set: set[int] = set()
    if period_ids:
        rev_period_rows = (
            db.query(ContractPeriod.id)
            .join(
                TransactionLine,
                TransactionLine.contract_id == ContractPeriod.contract_id,
            )
            .filter(
                ContractPeriod.id.in_(period_ids),
                TransactionLine.partner_id == partner_id,
                TransactionLine.line_type == "revenue",
                TransactionLine.revenue_month >= ContractPeriod.start_month,
                TransactionLine.revenue_month <= ContractPeriod.end_month,
            )
            .distinct()
            .all()
        )
        period_revenue_set = {r[0] for r in rev_period_rows}

        cost_period_rows = (
            db.query(ContractPeriod.id)
            .join(
                TransactionLine,
                TransactionLine.contract_id == ContractPeriod.contract_id,
            )
            .filter(
                ContractPeriod.id.in_(period_ids),
                TransactionLine.partner_id == partner_id,
                TransactionLine.line_type == "cost",
                TransactionLine.revenue_month >= ContractPeriod.start_month,
                TransactionLine.revenue_month <= ContractPeriod.end_month,
            )
            .distinct()
            .all()
        )
        period_cost_set = {r[0] for r in cost_period_rows}

    # Period별 담당자 관계
    period_contact_set: set[int] = set()
    if period_ids:
        contact_period_rows = (
            db.query(ContractContact.contract_period_id)
            .filter(
                ContractContact.contract_period_id.in_(period_ids),
                ContractContact.partner_id == partner_id,
            )
            .distinct()
            .all()
        )
        period_contact_set = {r[0] for r in contact_period_rows}

    # Period별 매출처 (ContractPeriod.partner_id)
    period_cust_set: set[int] = {
        p.id for p in all_periods if p.partner_id == partner_id
    }

    # ── 6) Period 단위 결과 생성 ──
    result = []
    total_revenue = 0
    active_count = 0
    completed_count = 0

    for p in all_periods:
        c = contract_map.get(p.contract_id)
        if not c:
            continue

        fin = fin_map.get(p.id, {"revenue": 0, "cost": 0})
        rev = fin["revenue"]
        cost = fin["cost"]
        gp_pct = round((rev - cost) / rev * 100, 1) if rev > 0 else None

        is_period_completed = p.is_completed

        # 기간 범위
        s = p.start_month[:7] if p.start_month else ""
        e = p.end_month[:7] if p.end_month else ""
        period_range = f"{s} ~ {e}" if s or e else ""

        # 역할 판별 (Period 단위)
        roles: list[str] = []
        is_revenue = p.id in period_cust_set or p.id in period_revenue_set
        if c.id in end_cust_ids and not is_revenue:
            roles.append("END고객")
        if is_revenue:
            roles.append("매출처")
        if p.id in period_cost_set:
            roles.append("매입처")
        if p.id in period_contact_set:
            roles.append("담당자")

        owner_name = c.owner.name if c.owner else None
        end_partner_name = c.end_partner.name if c.end_partner else None

        result.append({
            "id": c.id,
            "period_id": p.id,
            "period_label": p.period_label or f"Y{str(p.period_year)[-2:]}",
            "contract_code": c.contract_code,
            "contract_name": c.contract_name,
            "contract_type": c.contract_type,
            "status": c.status,
            "stage": p.stage or "",
            "is_completed": is_period_completed,
            "period_range": period_range,
            "revenue_amount": rev,
            "cost_amount": cost,
            "gp_pct": gp_pct,
            "end_partner_name": end_partner_name,
            "owner_name": owner_name,
            "roles": roles,
            "notes": c.notes,
        })

        if is_period_completed:
            completed_count += 1
        else:
            active_count += 1
        total_revenue += rev

    return {
        "summary": {
            "active_count": active_count,
            "completed_count": completed_count,
            "total_revenue": total_revenue,
        },
        "contracts": result,
    }


def list_partner_financials(db: Session, partner_id: int, current_user: User | None = None) -> dict:
    """거래처 기준 매출·매입 period 단위 집계 + 미수금.

    Returns:
        {"summary": {total_revenue, total_cost, ar}, "lines": [...]}
        lines: 사업 그룹 행(_is_group=True) + period 디테일 행
    """
    partner = db.get(Partner, partner_id)
    if not partner:
        raise NotFoundError("거래처를 찾을 수 없습니다.")

    related = list_related_contracts(db, partner_id, current_user=current_user)
    contract_ids = list({c["id"] for c in related["contracts"]})
    if not contract_ids:
        return {"summary": {"total_revenue": 0, "total_cost": 0, "ar": 0}, "lines": []}

    # period 조회 + 사업명 매핑
    all_periods = _build_period_lookup(db, contract_ids)
    contract_name_map: dict[int, str] = {}
    for c in related["contracts"]:
        contract_name_map.setdefault(c["id"], c["contract_name"])

    # 개별 TransactionLine 조회 → period 매칭
    txn_rows = (
        db.query(TransactionLine)
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.partner_id == partner_id,
        )
        .all()
    )

    # period별 집계: key = (contract_id, period_id)
    period_fin: dict[tuple[int, int], dict] = {}
    for txn in txn_rows:
        p = _match_period(all_periods, txn.contract_id, txn.revenue_month or "")
        pid = p.id if p else 0
        key = (txn.contract_id, pid)
        if key not in period_fin:
            period_fin[key] = {
                "contract_id": txn.contract_id,
                "period_id": pid,
                "period_label": (p.period_label or f"Y{str(p.period_year)[-2:]}") if p else "",
                "is_completed": p.is_completed if p else False,
                "revenue": 0,
                "cost": 0,
            }
        amt = txn.supply_amount or 0
        if txn.line_type == "revenue":
            period_fin[key]["revenue"] += amt
        elif txn.line_type == "cost":
            period_fin[key]["cost"] += amt

    # 사업별 그룹 + period 디테일 행 구성
    by_contract: dict[int, list[dict]] = defaultdict(list)
    for (cid, _pid), d in period_fin.items():
        by_contract[cid].append(d)

    total_revenue = 0
    total_cost = 0
    lines: list[dict] = []

    for cid in sorted(by_contract.keys(), key=lambda x: contract_name_map.get(x, "")):
        details = sorted(by_contract[cid], key=lambda x: x["period_label"])
        g_rev = sum(d["revenue"] for d in details)
        g_cost = sum(d["cost"] for d in details)
        g_gp = g_rev - g_cost
        g_gp_pct = round(g_gp / g_rev * 100, 1) if g_rev > 0 else None
        g_completed = all(d["is_completed"] for d in details)
        total_revenue += g_rev
        total_cost += g_cost

        # 그룹 행
        lines.append({
            "_is_group": True,
            "_group_key": cid,
            "contract_id": cid,
            "contract_name": contract_name_map.get(cid, ""),
            "period_label": "",
            "revenue": g_rev,
            "cost": g_cost,
            "gp": g_gp,
            "gp_pct": g_gp_pct,
            "is_completed": g_completed,
        })
        # 디테일 행
        for d in details:
            rev, cost = d["revenue"], d["cost"]
            gp = rev - cost
            gp_pct = round(gp / rev * 100, 1) if rev > 0 else None
            lines.append({
                "_is_group": False,
                "_group_key": cid,
                "contract_id": cid,
                "contract_name": "",
                "period_label": d["period_label"],
                "revenue": rev,
                "cost": cost,
                "gp": gp,
                "gp_pct": gp_pct,
                "is_completed": d["is_completed"],
            })

    # 미수금
    confirmed_revenue = (
        db.query(func.coalesce(func.sum(TransactionLine.supply_amount), 0))
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.partner_id == partner_id,
            TransactionLine.line_type == "revenue",
            TransactionLine.status == "확정",
        )
        .scalar()
    )
    matched_total = (
        db.query(func.coalesce(func.sum(ReceiptMatch.matched_amount), 0))
        .join(ReceiptMatch.transaction_line)
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.partner_id == partner_id,
            TransactionLine.line_type == "revenue",
        )
        .scalar()
    )
    ar = confirmed_revenue - matched_total

    return {
        "summary": {"total_revenue": total_revenue, "total_cost": total_cost, "ar": ar},
        "lines": lines,
    }


def list_partner_receipts(db: Session, partner_id: int, current_user: User | None = None) -> dict:
    """거래처 기준 입금 내역 + 미수금 잔액.

    Returns:
        {"summary": {total_receipt, ar_balance}, "receipts": [...]}
    """
    partner = db.get(Partner, partner_id)
    if not partner:
        raise NotFoundError("거래처를 찾을 수 없습니다.")

    # 접근 제어
    related = list_related_contracts(db, partner_id, current_user=current_user)
    contract_ids = [c["id"] for c in related["contracts"]]
    if not contract_ids:
        return {"summary": {"total_receipt": 0, "ar_balance": 0}, "receipts": []}

    rows = (
        db.query(Receipt)
        .filter(
            Receipt.contract_id.in_(contract_ids),
            Receipt.partner_id == partner_id,
        )
        .order_by(Receipt.contract_id, Receipt.receipt_date.desc())
        .all()
    )

    contract_name_map: dict[int, str] = {}
    for c in related["contracts"]:
        contract_name_map.setdefault(c["id"], c["contract_name"])

    all_periods = _build_period_lookup(db, contract_ids)

    # 사업+period별 그룹화
    by_group: dict[tuple[int, int], list[dict]] = defaultdict(list)
    total_receipt = 0

    for r in rows:
        total_receipt += r.amount
        p = _match_period(all_periods, r.contract_id, r.revenue_month or "")
        pid = p.id if p else 0
        by_group[(r.contract_id, pid)].append({
            "id": r.id,
            "receipt_date": r.receipt_date,
            "amount": r.amount,
            "description": r.description,
            "revenue_month": r.revenue_month[:7] if r.revenue_month and len(r.revenue_month) >= 7 else r.revenue_month,
        })

    # 그룹 행 + 디테일 행
    receipts: list[dict] = []
    by_contract: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for (cid, pid) in by_group:
        by_contract[cid].append((cid, pid))

    period_map = {p.id: p for p in all_periods}

    for cid in sorted(by_contract.keys(), key=lambda x: contract_name_map.get(x, "")):
        keys = sorted(by_contract[cid], key=lambda k: (period_map.get(k[1]).period_year if period_map.get(k[1]) else 0))
        c_total = sum(r["amount"] for k in keys for r in by_group[k])
        c_completed = all(period_map[k[1]].is_completed for k in keys if k[1] in period_map)

        # 사업 그룹 행
        receipts.append({
            "_is_group": True,
            "_group_key": cid,
            "contract_id": cid,
            "contract_name": contract_name_map.get(cid, ""),
            "period_label": "",
            "receipt_date": "",
            "amount": c_total,
            "description": f"{len([r for k in keys for r in by_group[k]])}건",
            "revenue_month": "",
            "is_completed": c_completed,
        })
        # period별 디테일 행
        for key in keys:
            p = period_map.get(key[1])
            p_label = (p.period_label or f"Y{str(p.period_year)[-2:]}") if p else ""
            p_completed = p.is_completed if p else False
            detail_rows = by_group[key]
            p_total = sum(r["amount"] for r in detail_rows)

            # period 소계 행
            receipts.append({
                "_is_group": True,
                "_group_key": cid,
                "_period_group": True,
                "contract_id": cid,
                "contract_name": "",
                "period_label": p_label,
                "receipt_date": "",
                "amount": p_total,
                "description": f"{len(detail_rows)}건",
                "revenue_month": "",
                "is_completed": p_completed,
            })
            # 개별 입금 행
            for dr in detail_rows:
                receipts.append({
                    "_is_group": False,
                    "_group_key": cid,
                    "contract_id": cid,
                    "contract_name": "",
                    "period_label": "",
                    "receipt_date": dr["receipt_date"],
                    "amount": dr["amount"],
                    "description": dr["description"],
                    "revenue_month": dr["revenue_month"],
                    "is_completed": p_completed,
                })

    # 미수금 잔액: 매출 확정 - ReceiptMatch 합계
    confirmed_revenue = (
        db.query(func.coalesce(func.sum(TransactionLine.supply_amount), 0))
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.partner_id == partner_id,
            TransactionLine.line_type == "revenue",
            TransactionLine.status == "확정",
        )
        .scalar()
    )
    matched_total = (
        db.query(func.coalesce(func.sum(ReceiptMatch.matched_amount), 0))
        .join(ReceiptMatch.transaction_line)
        .filter(
            TransactionLine.contract_id.in_(contract_ids),
            TransactionLine.partner_id == partner_id,
            TransactionLine.line_type == "revenue",
        )
        .scalar()
    )
    ar_balance = confirmed_revenue - matched_total

    return {
        "summary": {"total_receipt": total_receipt, "ar_balance": ar_balance},
        "receipts": receipts,
    }

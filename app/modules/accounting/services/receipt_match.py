"""수금 대사 (ReceiptMatch) 서비스.

핵심 로직:
- FIFO 자동 대사: Receipt의 귀속월이 속하는 ContractPeriod 범위 내 미대사 매출을 귀속월 순서로 대사
- 수동 대사: 사용자가 직접 대사 생성/수정/삭제
- 제약: receipt 초과 대사 불가, transaction_line 초과 대사 불가
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth.authorization import check_contract_access
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.accounting.models.contract_period import ContractPeriod
from app.modules.accounting.models.receipt_match import ReceiptMatch
from app.modules.accounting.models.transaction_line import TransactionLine, STATUS_CONFIRMED
from app.modules.accounting.models.receipt import Receipt
from app.modules.accounting.schemas.receipt_match import ReceiptMatchCreate, ReceiptMatchUpdate


# ── 조회 ─────────────────────────────────────────────────────────


def list_matches_by_contract(db: Session, contract_id: int) -> list[dict]:
    """Contract의 전체 대사 내역 조회."""
    rows = (
        db.query(ReceiptMatch)
        .join(ReceiptMatch.receipt)
        .join(ReceiptMatch.transaction_line)
        .filter(Receipt.contract_id == contract_id)
        .order_by(TransactionLine.revenue_month, ReceiptMatch.id)
        .all()
    )
    return [_match_dict(a) for a in rows]


def list_matches_by_receipt(db: Session, receipt_id: int) -> list[dict]:
    """특정 Receipt의 대사 내역 조회."""
    rows = (
        db.query(ReceiptMatch)
        .join(ReceiptMatch.transaction_line)
        .filter(ReceiptMatch.receipt_id == receipt_id)
        .order_by(TransactionLine.revenue_month)
        .all()
    )
    return [_match_dict(a) for a in rows]


def list_matches_by_transaction_line(db: Session, transaction_line_id: int) -> list[dict]:
    """특정 매출 라인의 대사 내역 조회."""
    rows = (
        db.query(ReceiptMatch)
        .join(ReceiptMatch.receipt)
        .filter(ReceiptMatch.transaction_line_id == transaction_line_id)
        .order_by(Receipt.receipt_date)
        .all()
    )
    return [_match_dict(a) for a in rows]


# ── FIFO 자동 대사 ───────────────────────────────────────────────


def auto_match_receipt(
    db: Session, receipt_id: int, *, created_by: int | None = None,
) -> list[ReceiptMatch]:
    """Receipt에 대해 FIFO 자동 대사 수행.

    기존 auto 대사를 모두 삭제하고 재계산한다.
    manual 대사는 유지한다.
    """
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise NotFoundError("수금 정보를 찾을 수 없습니다.")

    # 기존 auto 대사 삭제
    db.query(ReceiptMatch).filter(
        ReceiptMatch.receipt_id == receipt_id,
        ReceiptMatch.match_type == "auto",
    ).delete(synchronize_session="fetch")

    # manual 대사가 차지하는 금액
    manual_used = _sum_matched_for_receipt(db, receipt_id)
    remaining = receipt.amount - manual_used
    if remaining <= 0:
        return []

    # 같은 귀속기간의 미대사 매출 라인 (귀속월 ASC, id ASC)
    month_range = _get_period_month_range(db, receipt.contract_id, receipt.revenue_month)
    unmatched = _get_unmatched_sales(db, receipt.contract_id, month_range=month_range)

    created: list[ReceiptMatch] = []
    for transaction_line_id, supply_amount, already_matched in unmatched:
        if remaining <= 0:
            break
        available = supply_amount - already_matched
        if available <= 0:
            continue
        match_amount = min(remaining, available)
        match = ReceiptMatch(
            receipt_id=receipt_id,
            transaction_line_id=transaction_line_id,
            matched_amount=match_amount,
            match_type="auto",
            created_by=created_by,
        )
        db.add(match)
        created.append(match)
        remaining -= match_amount

    return created


def auto_match_contract(
    db: Session, contract_id: int, *, created_by: int | None = None,
) -> None:
    """Contract의 전체 Receipt에 대해 FIFO 자동 대사를 재계산.

    모든 auto 대사를 삭제하고, Receipt를 수금일 순서로 재대사한다.
    각 Receipt는 귀속월이 속하는 ContractPeriod 범위 내 매출만 대상으로 한다.
    """
    try:
        receipt_ids = [
            rid for (rid,) in
            db.query(Receipt.id).filter(Receipt.contract_id == contract_id).all()
        ]
        if not receipt_ids:
            return

        db.query(ReceiptMatch).filter(
            ReceiptMatch.receipt_id.in_(receipt_ids),
            ReceiptMatch.match_type == "auto",
        ).delete(synchronize_session="fetch")

        receipts = (
            db.query(Receipt)
            .filter(Receipt.contract_id == contract_id)
            .order_by(Receipt.receipt_date, Receipt.id)
            .all()
        )

        for rcpt in receipts:
            manual_used = _sum_matched_for_receipt(db, rcpt.id)
            remaining = rcpt.amount - manual_used
            if remaining <= 0:
                continue

            db.flush()
            month_range = _get_period_month_range(db, contract_id, rcpt.revenue_month)
            unmatched = _get_unmatched_sales(db, contract_id, month_range=month_range)
            for transaction_line_id, supply_amount, already_matched in unmatched:
                if remaining <= 0:
                    break
                available = supply_amount - already_matched
                if available <= 0:
                    continue
                match_amount = min(remaining, available)
                db.add(ReceiptMatch(
                    receipt_id=rcpt.id,
                    transaction_line_id=transaction_line_id,
                    matched_amount=match_amount,
                    match_type="auto",
                    created_by=created_by,
                ))
                remaining -= match_amount

        db.commit()
    except Exception:
        db.rollback()
        raise


# ── 수동 대사 CRUD ───────────────────────────────────────────────


def create_match(
    db: Session,
    data: ReceiptMatchCreate,
    *,
    created_by: int | None = None,
    current_user=None,
    expected_contract_id: int | None = None,
) -> dict:
    """수동 대사 생성."""
    try:
        contract_id = _validate_match(
            db,
            data.receipt_id,
            data.transaction_line_id,
            data.matched_amount,
        )
        if expected_contract_id is not None and contract_id != expected_contract_id:
            raise BusinessRuleError("요청 경로의 사업과 대사 대상 사업이 일치하지 않습니다.")
        if current_user is not None:
            check_contract_access(db, contract_id, current_user)

        match = ReceiptMatch(
            receipt_id=data.receipt_id,
            transaction_line_id=data.transaction_line_id,
            matched_amount=data.matched_amount,
            match_type=data.match_type,
            created_by=created_by,
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        return _match_dict(match)
    except Exception:
        db.rollback()
        raise


def update_match(
    db: Session,
    match_id: int,
    data: ReceiptMatchUpdate,
    *,
    current_user=None,
) -> dict:
    """대사 금액 수정."""
    try:
        match = db.get(ReceiptMatch, match_id)
        if not match:
            raise NotFoundError("대사 정보를 찾을 수 없습니다.")
        contract_id = match.receipt.contract_id if match.receipt else None
        if contract_id is None:
            raise NotFoundError("대사에 연결된 수금 정보를 찾을 수 없습니다.")
        if current_user is not None:
            check_contract_access(db, contract_id, current_user)

        _validate_match(
            db, match.receipt_id, match.transaction_line_id,
            data.matched_amount, exclude_match_id=match_id,
        )
        match.matched_amount = data.matched_amount
        match.match_type = "manual"
        db.commit()
        return _match_dict(match)
    except Exception:
        db.rollback()
        raise


def delete_match(db: Session, match_id: int, *, current_user=None) -> None:
    """대사 삭제."""
    try:
        match = db.get(ReceiptMatch, match_id)
        if not match:
            raise NotFoundError("대사 정보를 찾을 수 없습니다.")
        contract_id = match.receipt.contract_id if match.receipt else None
        if contract_id is None:
            raise NotFoundError("대사에 연결된 수금 정보를 찾을 수 없습니다.")
        if current_user is not None:
            check_contract_access(db, contract_id, current_user)
        db.delete(match)
        db.commit()
    except Exception:
        db.rollback()
        raise


# ── 집계 헬퍼 (metrics 등에서 사용) ──────────────────────────────


def get_matched_sum_by_contract(db: Session, contract_ids: list[int]) -> dict[int, int]:
    """contract_id → 대사완료 합계."""
    if not contract_ids:
        return {}
    rows = (
        db.query(Receipt.contract_id, func.sum(ReceiptMatch.matched_amount))
        .join(ReceiptMatch, ReceiptMatch.receipt_id == Receipt.id)
        .filter(Receipt.contract_id.in_(contract_ids))
        .group_by(Receipt.contract_id)
        .all()
    )
    return {did: int(total or 0) for did, total in rows}


def get_matched_sum_by_transaction_line(
    db: Session, transaction_line_ids: list[int],
) -> dict[int, int]:
    """transaction_line_id → 대사완료 합계."""
    if not transaction_line_ids:
        return {}
    rows = (
        db.query(ReceiptMatch.transaction_line_id, func.sum(ReceiptMatch.matched_amount))
        .filter(ReceiptMatch.transaction_line_id.in_(transaction_line_ids))
        .group_by(ReceiptMatch.transaction_line_id)
        .all()
    )
    return {aid: int(total or 0) for aid, total in rows}


def get_matched_sum_by_contract_monthly(
    db: Session, contract_ids: list[int], date_from: str, date_to: str,
) -> dict[int, dict[str, int]]:
    """contract_id → month → 대사완료 합계."""
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


# ── Private 헬퍼 ─────────────────────────────────────────────────


def _match_dict(a: ReceiptMatch) -> dict:
    transaction_line = a.transaction_line
    receipt = a.receipt
    return {
        "id": a.id,
        "receipt_id": a.receipt_id,
        "transaction_line_id": a.transaction_line_id,
        "matched_amount": a.matched_amount,
        "match_type": a.match_type,
        "receipt_date": receipt.receipt_date if receipt else None,
        "revenue_month": transaction_line.revenue_month if transaction_line else None,
        "partner_name": transaction_line.partner.name if transaction_line and transaction_line.partner else None,
        "supply_amount": transaction_line.supply_amount if transaction_line else None,
    }


def _sum_matched_for_receipt(
    db: Session, receipt_id: int, *, exclude_match_id: int | None = None,
) -> int:
    """Receipt에 이미 대사된 총액."""
    q = db.query(func.coalesce(func.sum(ReceiptMatch.matched_amount), 0)).filter(
        ReceiptMatch.receipt_id == receipt_id,
    )
    if exclude_match_id:
        q = q.filter(ReceiptMatch.id != exclude_match_id)
    return int(q.scalar())


def _sum_matched_for_transaction_line(
    db: Session, transaction_line_id: int, *, exclude_match_id: int | None = None,
) -> int:
    """매출 라인에 이미 대사된 총액."""
    q = db.query(func.coalesce(func.sum(ReceiptMatch.matched_amount), 0)).filter(
        ReceiptMatch.transaction_line_id == transaction_line_id,
    )
    if exclude_match_id:
        q = q.filter(ReceiptMatch.id != exclude_match_id)
    return int(q.scalar())


def _get_period_month_range(
    db: Session, contract_id: int, revenue_month: str | None,
) -> tuple[str, str] | None:
    """입금의 revenue_month가 속하는 ContractPeriod의 월 범위를 반환.

    해당하는 기간이 없으면 None (전체 계약 대상 fallback).
    """
    if not revenue_month:
        return None
    period = (
        db.query(ContractPeriod)
        .filter(
            ContractPeriod.contract_id == contract_id,
            ContractPeriod.start_month <= revenue_month,
            ContractPeriod.end_month >= revenue_month,
        )
        .first()
    )
    if not period or not period.start_month or not period.end_month:
        return None
    return (period.start_month, period.end_month)


def _get_unmatched_sales(
    db: Session,
    contract_id: int,
    *,
    month_range: tuple[str, str] | None = None,
) -> list[tuple[int, int, int]]:
    """미대사 매출 라인 목록: [(transaction_line_id, supply_amount, already_matched), ...]

    귀속월 ASC, id ASC 순서 (FIFO).
    month_range가 주어지면 해당 기간의 매출만 대상으로 한다.
    """
    matched_sub = (
        db.query(
            ReceiptMatch.transaction_line_id,
            func.coalesce(func.sum(ReceiptMatch.matched_amount), 0).label("total"),
        )
        .group_by(ReceiptMatch.transaction_line_id)
        .subquery()
    )

    q = (
        db.query(
            TransactionLine.id,
            TransactionLine.supply_amount,
            func.coalesce(matched_sub.c.total, 0),
        )
        .outerjoin(matched_sub, matched_sub.c.transaction_line_id == TransactionLine.id)
        .filter(
            TransactionLine.contract_id == contract_id,
            TransactionLine.line_type == "revenue",
            TransactionLine.status == STATUS_CONFIRMED,
            func.coalesce(matched_sub.c.total, 0) < TransactionLine.supply_amount,
        )
    )
    if month_range:
        q = q.filter(
            TransactionLine.revenue_month >= month_range[0],
            TransactionLine.revenue_month <= month_range[1],
        )
    rows = q.order_by(TransactionLine.revenue_month, TransactionLine.id).all()
    return [(r[0], int(r[1]), int(r[2])) for r in rows]


def _validate_match(
    db: Session,
    receipt_id: int,
    transaction_line_id: int,
    amount: int,
    *,
    exclude_match_id: int | None = None,
) -> int:
    """대사 제약 검증."""
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise NotFoundError("수금 정보를 찾을 수 없습니다.")

    transaction_line = db.get(TransactionLine, transaction_line_id)
    if not transaction_line:
        raise NotFoundError("매출 실적을 찾을 수 없습니다.")

    if transaction_line.line_type != "revenue":
        raise BusinessRuleError("매출(revenue) 라인에만 대사할 수 있습니다.")

    if receipt.contract_id != transaction_line.contract_id:
        raise BusinessRuleError("같은 사업의 수금과 매출만 대사할 수 있습니다.")

    # Receipt 초과 검증
    used_receipt = _sum_matched_for_receipt(
        db, receipt_id, exclude_match_id=exclude_match_id,
    )
    if used_receipt + amount > receipt.amount:
        raise BusinessRuleError(
            f"수금 금액({receipt.amount:,}원)을 초과하여 대사할 수 없습니다. "
            f"현재 대사: {used_receipt:,}원, 요청: {amount:,}원"
        )

    # TransactionLine 초과 검증
    used_transaction_line = _sum_matched_for_transaction_line(
        db, transaction_line_id, exclude_match_id=exclude_match_id,
    )
    if used_transaction_line + amount > transaction_line.supply_amount:
        raise BusinessRuleError(
            f"매출 금액({transaction_line.supply_amount:,}원)을 초과하여 대사할 수 없습니다. "
            f"현재 대사: {used_transaction_line:,}원, 요청: {amount:,}원"
        )

    return receipt.contract_id

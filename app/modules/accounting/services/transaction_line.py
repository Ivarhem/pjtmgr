"""TransactionLine(매출/매입 실적) 서비스."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from app.core.auth.authorization import can_delete_transaction_line, check_contract_access
from app.core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from app.modules.accounting.models.contract import Contract
from app.modules.accounting.models.transaction_line import (
    STATUS_CONFIRMED,
    STATUS_EXPECTED,
    TransactionLine,
)
from app.modules.accounting.schemas.transaction_line import TransactionLineCreate, TransactionLineUpdate
from app.modules.accounting.services._contract_helpers import (
    check_period_not_completed,
    check_periods_not_completed,
)
from app.modules.common.services.partner import get_or_create_by_name as _get_or_create_partner

if TYPE_CHECKING:
    from app.modules.common.models.user import User


# ── dict 변환 ─────────────────────────────────────────────

def _transaction_line_dict(a: TransactionLine) -> dict:
    return {
        "id": a.id,
        "contract_id": a.contract_id,
        "revenue_month": a.revenue_month,
        "line_type": a.line_type,
        "partner_id": a.partner_id,
        "partner_name": a.partner.name if a.partner else None,
        "supply_amount": a.supply_amount,
        "invoice_issue_date": a.invoice_issue_date,
        "status": a.status or "확정",
        "description": a.description,
    }


# ── 내부 헬퍼 ─────────────────────────────────────────────

def _auto_status(fields: dict) -> str:
    """거래처·발행일 유무로 상태를 자동 판별."""
    has_partner = fields.get("partner_id") is not None
    has_date = bool(fields.get("invoice_issue_date"))
    return STATUS_CONFIRMED if (has_partner and has_date) else STATUS_EXPECTED


def _resolve_partner(db: Session, data_dict: dict) -> dict:
    """partner_id가 없고 partner_name이 있으면 자동 생성/조회."""
    name = data_dict.pop("partner_name", None)
    if not data_dict.get("partner_id") and name and name.strip():
        partner = _get_or_create_partner(db, name.strip())
        data_dict["partner_id"] = partner.id
    return data_dict


# ── CRUD ──────────────────────────────────────────────────

def get_transaction_lines(db: Session, contract_id: int) -> list[dict]:
    return _get_transaction_lines(db, contract_id)


def _get_transaction_lines(db: Session, contract_id: int) -> list[dict]:
    rows = (
        db.query(TransactionLine)
        .options(joinedload(TransactionLine.partner))
        .filter(TransactionLine.contract_id == contract_id)
        .order_by(TransactionLine.revenue_month, TransactionLine.line_type)
        .all()
    )
    return [_transaction_line_dict(r) for r in rows]


def create_transaction_line(
    db: Session,
    contract_id: int,
    data: TransactionLineCreate,
    *,
    created_by: int | None = None,
    current_user: User | None = None,
) -> dict:
    try:
        if current_user:
            check_contract_access(db, contract_id, current_user)
        contract = db.get(Contract, contract_id)
        if not contract:
            raise NotFoundError("사업을 찾을 수 없습니다.")
        if contract.status == "cancelled":
            raise BusinessRuleError("삭제된 사업에는 매출/매입을 추가할 수 없습니다.")
        check_period_not_completed(db, contract_id, data.revenue_month)
        fields = _resolve_partner(db, data.model_dump())
        if not fields.get("status"):
            fields["status"] = _auto_status(fields)
        row = TransactionLine(contract_id=contract_id, created_by=created_by, **fields)
        db.add(row)
        db.commit()
        db.refresh(row)
        return _transaction_line_dict(row)
    except Exception:
        db.rollback()
        raise


def list_transaction_lines_for_contract(
    db: Session,
    contract_id: int,
    *,
    current_user: User | None = None,
) -> list[dict]:
    if current_user:
        check_contract_access(db, contract_id, current_user)
    return _get_transaction_lines(db, contract_id)


def update_transaction_line(
    db: Session,
    transaction_line_id: int,
    data: TransactionLineUpdate,
    *,
    current_user: User | None = None,
) -> dict:
    try:
        row = (
            db.query(TransactionLine)
            .options(joinedload(TransactionLine.partner))
            .filter(TransactionLine.id == transaction_line_id)
            .first()
        )
        if not row:
            raise NotFoundError("실적을 찾을 수 없습니다.")
        if current_user:
            check_contract_access(db, row.contract_id, current_user)
        fields = _resolve_partner(db, data.model_dump(exclude_unset=True))
        check_periods_not_completed(
            db,
            row.contract_id,
            row.revenue_month,
            fields.get("revenue_month", row.revenue_month),
        )
        for field, value in fields.items():
            setattr(row, field, value)
        db.commit()
        db.refresh(row)
        return _transaction_line_dict(row)
    except Exception:
        db.rollback()
        raise


def delete_transaction_line(
    db: Session, transaction_line_id: int, *, current_user: User | None = None
) -> None:
    try:
        row = db.get(TransactionLine, transaction_line_id)
        if not row:
            raise NotFoundError("실적을 찾을 수 없습니다.")
        if current_user:
            if not can_delete_transaction_line(current_user):
                raise PermissionDeniedError("실적 삭제 권한이 없습니다.")
            check_contract_access(db, row.contract_id, current_user)
        check_period_not_completed(db, row.contract_id, row.revenue_month)
        from app.modules.accounting.models.receipt_match import ReceiptMatch
        from sqlalchemy import func as sa_func

        matched = (
            db.query(sa_func.coalesce(sa_func.sum(ReceiptMatch.matched_amount), 0))
            .filter(ReceiptMatch.transaction_line_id == transaction_line_id)
            .scalar()
        )
        if matched and matched > 0:
            raise BusinessRuleError(
                "입금 매칭이 존재하는 행은 삭제할 수 없습니다. 매칭을 먼저 해제하세요."
            )
        db.delete(row)
        db.commit()
    except Exception:
        db.rollback()
        raise


def bulk_confirm_transaction_lines(
    db: Session,
    contract_id: int,
    *,
    current_user: User | None = None,
) -> dict:
    """거래처+발행일이 있는 '예정' 매출/매입 행을 일괄 확정 처리."""
    try:
        if current_user:
            check_contract_access(db, contract_id, current_user)
        rows = (
            db.query(TransactionLine)
            .filter(
                TransactionLine.contract_id == contract_id,
                TransactionLine.status == STATUS_EXPECTED,
                TransactionLine.partner_id.isnot(None),
                TransactionLine.invoice_issue_date.isnot(None),
                TransactionLine.invoice_issue_date != "",
            )
            .all()
        )
        for row in rows:
            row.status = STATUS_CONFIRMED
        db.commit()
        return {"confirmed": len(rows)}
    except Exception:
        db.rollback()
        raise

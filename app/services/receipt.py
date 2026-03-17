"""Receipt(입금) 서비스."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from app.auth.authorization import check_contract_access
from app.exceptions import BusinessRuleError, NotFoundError
from app.models.contract import Contract
from app.models.receipt import Receipt
from app.schemas.receipt import ReceiptCreate, ReceiptUpdate
from app.services._contract_helpers import (
    check_period_not_completed,
    check_periods_not_completed,
)

if TYPE_CHECKING:
    from app.models.user import User


def _receipt_dict(p: Receipt) -> dict:
    return {
        "id": p.id,
        "contract_id": p.contract_id,
        "customer_id": p.customer_id,
        "customer_name": p.customer.name if p.customer else None,
        "receipt_date": p.receipt_date,
        "revenue_month": p.revenue_month,
        "amount": p.amount,
        "description": p.description,
    }


def get_receipts(db: Session, contract_id: int) -> list[dict]:
    return _get_receipts(db, contract_id)


def _get_receipts(db: Session, contract_id: int) -> list[dict]:
    rows = (
        db.query(Receipt)
        .options(joinedload(Receipt.customer))
        .filter(Receipt.contract_id == contract_id)
        .order_by(Receipt.receipt_date)
        .all()
    )
    return [_receipt_dict(r) for r in rows]


def create_receipt(
    db: Session,
    contract_id: int,
    data: ReceiptCreate,
    *,
    created_by: int | None = None,
    current_user: User | None = None,
) -> dict:
    from app.services.receipt_match import auto_match_receipt

    try:
        if current_user:
            check_contract_access(db, contract_id, current_user)
        contract = db.get(Contract, contract_id)
        if not contract:
            raise NotFoundError("사업을 찾을 수 없습니다.")
        if contract.status == "cancelled":
            raise BusinessRuleError("삭제된 사업에는 입금을 추가할 수 없습니다.")
        check_period_not_completed(db, contract_id, data.revenue_month)
        row = Receipt(contract_id=contract_id, created_by=created_by, **data.model_dump())
        db.add(row)
        db.flush()
        auto_match_receipt(db, row.id, created_by=created_by)
        db.commit()
        db.refresh(row)
        return _receipt_dict(row)
    except Exception:
        db.rollback()
        raise


def list_receipts_for_contract(
    db: Session,
    contract_id: int,
    *,
    current_user: User | None = None,
) -> list[dict]:
    if current_user:
        check_contract_access(db, contract_id, current_user)
    return _get_receipts(db, contract_id)


def update_receipt(
    db: Session,
    receipt_id: int,
    data: ReceiptUpdate,
    *,
    current_user: User | None = None,
) -> dict:
    from app.services.receipt_match import auto_match_receipt

    try:
        row = (
            db.query(Receipt)
            .options(joinedload(Receipt.customer))
            .filter(Receipt.id == receipt_id)
            .first()
        )
        if not row:
            raise NotFoundError("입금 정보를 찾을 수 없습니다.")
        if current_user:
            check_contract_access(db, row.contract_id, current_user)
        updates = data.model_dump(exclude_unset=True)
        check_periods_not_completed(
            db,
            row.contract_id,
            row.revenue_month,
            updates.get("revenue_month", row.revenue_month),
        )
        for field, value in updates.items():
            setattr(row, field, value)
        if "amount" in updates:
            auto_match_receipt(
                db, receipt_id, created_by=current_user.id if current_user else None
            )
        db.commit()
        db.refresh(row)
        return _receipt_dict(row)
    except Exception:
        db.rollback()
        raise


def delete_receipt(db: Session, receipt_id: int) -> None:
    try:
        row = db.get(Receipt, receipt_id)
        if not row:
            raise NotFoundError("입금 정보를 찾을 수 없습니다.")
        check_period_not_completed(db, row.contract_id, row.revenue_month)
        db.delete(row)
        db.commit()
    except Exception:
        db.rollback()
        raise

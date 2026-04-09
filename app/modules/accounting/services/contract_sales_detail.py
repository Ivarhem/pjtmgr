from __future__ import annotations
import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Session
from app.core.auth.authorization import check_period_access
from app.modules.accounting.models.contract_sales_detail import ContractSalesDetail
from app.modules.accounting.schemas.contract_sales_detail import ContractSalesDetailUpdate

if TYPE_CHECKING:
    from app.modules.common.models.user import User


def get_or_create_sales_detail(
    db: Session, period_id: int, *, current_user: User | None = None
) -> dict:
    if current_user:
        check_period_access(db, period_id, current_user)
    detail = db.query(ContractSalesDetail).filter(
        ContractSalesDetail.contract_period_id == period_id
    ).first()
    if not detail:
        detail = ContractSalesDetail(contract_period_id=period_id)
        db.add(detail)
        db.commit()
        db.refresh(detail)
    return _to_dict(detail)


def update_sales_detail(
    db: Session, period_id: int, data: ContractSalesDetailUpdate,
    *, current_user: User | None = None
) -> dict:
    if current_user:
        check_period_access(db, period_id, current_user)
    detail = db.query(ContractSalesDetail).filter(
        ContractSalesDetail.contract_period_id == period_id
    ).first()
    if not detail:
        detail = ContractSalesDetail(contract_period_id=period_id)
        db.add(detail)
        db.flush()
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "inspection_date" and isinstance(value, str):
            value = datetime.date.fromisoformat(value)
        setattr(detail, field, value)
    db.commit()
    db.refresh(detail)
    return _to_dict(detail)


def _to_dict(detail: ContractSalesDetail) -> dict:
    return {
        "id": detail.id,
        "contract_period_id": detail.contract_period_id,
        "expected_revenue_amount": detail.expected_revenue_amount,
        "expected_gp_amount": detail.expected_gp_amount,
        "inspection_day": detail.inspection_day,
        "inspection_date": str(detail.inspection_date) if detail.inspection_date else None,
        "invoice_month_offset": detail.invoice_month_offset,
        "invoice_day_type": detail.invoice_day_type,
        "invoice_day": detail.invoice_day,
        "invoice_holiday_adjust": detail.invoice_holiday_adjust,
    }

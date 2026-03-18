"""Ledger(매출/매입 실적 원장) 서비스."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.modules.accounting.services.transaction_line import list_transaction_lines_for_contract

if TYPE_CHECKING:
    from app.modules.common.models.user import User


def get_ledger(db: Session, contract_id: int, *, current_user: User | None = None) -> list[dict]:
    """매출/매입 실적 원장"""
    transaction_lines = list_transaction_lines_for_contract(
        db,
        contract_id,
        current_user=current_user,
    )

    rows: list[dict] = []
    for a in transaction_lines:
        rows.append(
            {
                "row_key": f"a_{a['id']}",
                "record_type": "transaction_line",
                "transaction_line_id": a["id"],
                "type": "매출" if a["line_type"] == "revenue" else "매입",
                "revenue_month": a["revenue_month"],
                "date": a["invoice_issue_date"],
                "customer_name": a["customer_name"],
                "amount": a["supply_amount"],
                "status": a["status"],
                "description": a["description"],
            }
        )

    rows.sort(key=lambda r: (r["revenue_month"] or "9999-99-99", r.get("date") or ""))
    return rows

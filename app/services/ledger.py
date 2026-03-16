"""Ledger(매출/매입 실적 원장) 서비스."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.transaction_line import get_transaction_lines


def get_ledger(db: Session, contract_id: int) -> list[dict]:
    """매출/매입 실적 원장"""
    transaction_lines = get_transaction_lines(db, contract_id)

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

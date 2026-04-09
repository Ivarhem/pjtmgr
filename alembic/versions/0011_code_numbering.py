"""Hierarchical code numbering: C000-P000-Y26A.

Revision ID: 0011
Revises: 0010
Create Date: 2026-03-23

NON-REVERSIBLE: 기존 코드 형식이 파괴됨. 실행 전 DB 백업 권장.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def _int_to_base36(n: int, width: int = 3) -> str:
    result = []
    for _ in range(width):
        result.append(_BASE36[n % 36])
        n //= 36
    return "".join(reversed(result))


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step 1: customer_code 변환 (C-000 → C000) ──
    conn.execute(text(
        "UPDATE customers SET customer_code = REPLACE(customer_code, 'C-', 'C') "
        "WHERE customer_code LIKE 'C-%'"
    ))

    # ── Step 2: contract_code 재채번 ──
    # 고객별로 사업을 id 순 정렬, {customer_code}-P{seq} 형식으로 재채번
    contracts = conn.execute(text(
        "SELECT c.id, c.end_customer_id, "
        "  COALESCE(cu.customer_code, 'CXXX') AS cust_code "
        "FROM contracts c "
        "LEFT JOIN customers cu ON cu.id = c.end_customer_id "
        "ORDER BY COALESCE(cu.customer_code, 'CXXX'), c.id"
    )).fetchall()

    cust_seq: dict[str, int] = {}  # customer_code → next seq
    for row in contracts:
        cust_code = row[2]
        seq = cust_seq.get(cust_code, 0)
        new_code = f"{cust_code}-P{_int_to_base36(seq)}"
        conn.execute(text(
            "UPDATE contracts SET contract_code = :code WHERE id = :id"
        ), {"code": new_code, "id": row[0]})
        cust_seq[cust_code] = seq + 1

    # ── Step 3: period_code 컬럼 추가 및 채번 ──
    op.add_column("contract_periods", sa.Column("period_code", sa.String(14), nullable=True))

    periods = conn.execute(text(
        "SELECT cp.id, cp.period_year, c.contract_code "
        "FROM contract_periods cp "
        "JOIN contracts c ON c.id = cp.contract_id "
        "ORDER BY c.contract_code, cp.period_year, cp.id"
    )).fetchall()

    contract_year_seq: dict[str, int] = {}  # "{contract_code}-Y{yy}" → next letter index
    for row in periods:
        period_id, period_year, contract_code = row[0], row[1], row[2]
        year_suffix = f"Y{period_year % 100:02d}"
        key = f"{contract_code}-{year_suffix}"
        letter_idx = contract_year_seq.get(key, 0)
        letter = chr(ord("A") + letter_idx)
        period_code = f"{key}{letter}"
        conn.execute(text(
            "UPDATE contract_periods SET period_code = :code WHERE id = :id"
        ), {"code": period_code, "id": period_id})
        contract_year_seq[key] = letter_idx + 1

    # NOT NULL + UNIQUE
    op.alter_column("contract_periods", "period_code", nullable=False)
    op.create_index("ix_contract_periods_period_code", "contract_periods", ["period_code"], unique=True)

    # ── Step 4: 컬럼 크기 조정 (안전 검증) ──
    overflow = conn.execute(text(
        "SELECT COUNT(*) FROM customers WHERE LENGTH(customer_code) > 4"
    )).scalar()
    assert overflow == 0, f"customer_code 길이 초과 행 {overflow}건 — 마이그레이션 중단"

    overflow = conn.execute(text(
        "SELECT COUNT(*) FROM contracts WHERE LENGTH(contract_code) > 9"
    )).scalar()
    assert overflow == 0, f"contract_code 길이 초과 행 {overflow}건 — 마이그레이션 중단"

    op.alter_column("customers", "customer_code",
                     type_=sa.String(4), existing_type=sa.String(10))
    op.alter_column("contracts", "contract_code",
                     type_=sa.String(9), existing_type=sa.String(50), nullable=False)


def downgrade() -> None:
    raise NotImplementedError("비가역 마이그레이션 — downgrade 불가")

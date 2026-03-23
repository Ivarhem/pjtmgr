"""Add customer_code column to customers table with auto-generated values.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _int_to_base36(n: int, width: int = 3) -> str:
    result = []
    for _ in range(width):
        result.append(_BASE36_CHARS[n % 36])
        n //= 36
    return "".join(reversed(result))


def upgrade() -> None:
    # 1. Add column as nullable first
    op.add_column("customers", sa.Column("customer_code", sa.String(10), nullable=True))

    # 2. Backfill existing rows with sequential codes
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id FROM customers ORDER BY id")).fetchall()
    for i, row in enumerate(rows):
        code = f"C-{_int_to_base36(i)}"
        conn.execute(
            text("UPDATE customers SET customer_code = :code WHERE id = :id"),
            {"code": code, "id": row[0]},
        )

    # 3. Make non-nullable and add unique index
    op.alter_column("customers", "customer_code", nullable=False)
    op.create_index("ix_customers_customer_code", "customers", ["customer_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_customers_customer_code", table_name="customers")
    op.drop_column("customers", "customer_code")

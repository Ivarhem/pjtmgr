"""add login_failures table

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-16
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect as sa_inspect
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if "login_failures" in inspector.get_table_names():
        return
    op.create_table(
        "login_failures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login_id", sa.String(100), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_login_failures_login_id", "login_failures", ["login_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_login_failures_login_id", table_name="login_failures")
    op.drop_table("login_failures")

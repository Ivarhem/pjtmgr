"""Add project_contract_links table and audit_logs.module column.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    """Check if table already exists (idempotent)."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return name in inspector.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    """Check if column already exists in table (idempotent)."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    # -- project_contract_links --
    if not _table_exists("project_contract_links"):
        op.create_table(
            "project_contract_links",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("projects.id"),
                nullable=False,
            ),
            sa.Column(
                "contract_id",
                sa.Integer(),
                sa.ForeignKey("contracts.id"),
                nullable=False,
            ),
            sa.Column(
                "is_primary",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint("project_id", "contract_id", name="uq_project_contract_link"),
        )

    # -- audit_logs.module column --
    if _table_exists("audit_logs") and not _column_exists("audit_logs", "module"):
        op.add_column(
            "audit_logs",
            sa.Column("module", sa.String(20), nullable=True, index=True),
        )


def downgrade() -> None:
    # Drop module column from audit_logs
    if _table_exists("audit_logs") and _column_exists("audit_logs", "module"):
        op.drop_column("audit_logs", "module")

    # Drop project_contract_links table
    if _table_exists("project_contract_links"):
        op.drop_table("project_contract_links")

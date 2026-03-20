"""Add project_customers and project_customer_contacts tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # -- project_customers --
    if not _table_exists("project_customers"):
        op.create_table(
            "project_customers",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("projects.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "customer_id",
                sa.Integer(),
                sa.ForeignKey("customers.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("scope_text", sa.String(500), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("project_id", "customer_id", "role"),
        )

    # -- project_customer_contacts --
    if not _table_exists("project_customer_contacts"):
        op.create_table(
            "project_customer_contacts",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column(
                "project_customer_id",
                sa.Integer(),
                sa.ForeignKey("project_customers.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "contact_id",
                sa.Integer(),
                sa.ForeignKey("customer_contacts.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("project_role", sa.String(100), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "project_customer_id", "contact_id", "project_role"
            ),
        )


def downgrade() -> None:
    op.drop_table("project_customer_contacts")
    op.drop_table("project_customers")

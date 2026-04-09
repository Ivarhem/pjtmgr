"""Add capacity_type to hardware_interfaces.

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hardware_interfaces",
        sa.Column(
            "capacity_type",
            sa.String(10),
            nullable=False,
            server_default="fixed",
        ),
    )


def downgrade() -> None:
    op.drop_column("hardware_interfaces", "capacity_type")

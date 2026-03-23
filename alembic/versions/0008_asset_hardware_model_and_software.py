"""Add hardware_model_id FK to assets, create asset_software table.

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # assets 테이블에 hardware_model_id FK 추가
    op.add_column(
        "assets",
        sa.Column(
            "hardware_model_id",
            sa.Integer,
            sa.ForeignKey("product_catalog.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # asset_software 테이블 생성
    op.create_table(
        "asset_software",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "asset_id",
            sa.Integer,
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("software_name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(100), nullable=True),
        sa.Column("license_type", sa.String(50), nullable=True),
        sa.Column("license_count", sa.Integer, nullable=True),
        sa.Column("relation_type", sa.String(30), nullable=False, server_default="installed"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("asset_software")
    op.drop_column("assets", "hardware_model_id")

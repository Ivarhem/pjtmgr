# -*- coding: utf-8 -*-
"""add product_catalog_list_cache table

Revision ID: 0056
Revises: 0055
Create Date: 2026-04-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0056"
down_revision = "0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_catalog_list_cache",
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("layout_id", sa.Integer(), sa.ForeignKey("classification_layouts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("cached_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_product_catalog_list_cache_layout",
        "product_catalog_list_cache",
        ["layout_id"],
    )


def downgrade() -> None:
    op.drop_table("product_catalog_list_cache")

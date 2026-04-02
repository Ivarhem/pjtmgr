# -*- coding: utf-8 -*-
"""drop legacy classification columns from product_catalog

Revision ID: 0044
Revises: 0043
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("product_catalog", "classification_node_code")
    op.drop_column("product_catalog", "category")


def downgrade() -> None:
    op.add_column(
        "product_catalog",
        sa.Column("category", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "product_catalog",
        sa.Column("classification_node_code", sa.String(length=50), nullable=True),
    )
    op.create_index(
        op.f("ix_product_catalog_classification_node_code"),
        "product_catalog",
        ["classification_node_code"],
        unique=False,
    )

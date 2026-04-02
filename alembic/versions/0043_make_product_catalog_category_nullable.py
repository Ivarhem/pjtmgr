# -*- coding: utf-8 -*-
"""make product_catalog.category nullable

Revision ID: 0043
Revises: 0042
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "product_catalog",
        "category",
        existing_type=sa.String(length=50),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE product_catalog SET category = 'generic' WHERE category IS NULL"
        )
    )
    op.alter_column(
        "product_catalog",
        "category",
        existing_type=sa.String(length=50),
        nullable=False,
    )

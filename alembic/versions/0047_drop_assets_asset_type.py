# -*- coding: utf-8 -*-
"""drop assets asset_type

Revision ID: 0047
Revises: 0046
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("assets")}
    if "asset_type" in columns:
        op.drop_column("assets", "asset_type")


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")

# -*- coding: utf-8 -*-
"""drop legacy classification tables

Revision ID: 0045
Revises: 0044
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    asset_columns = {column["name"] for column in inspector.get_columns("assets")}
    if "classification_node_id" in asset_columns:
        fk_names = [
            fk["name"]
            for fk in inspector.get_foreign_keys("assets")
            if "classification_node_id" in (fk.get("constrained_columns") or [])
        ]
        for fk_name in fk_names:
            op.drop_constraint(fk_name, "assets", type_="foreignkey")
        op.drop_column("assets", "classification_node_id")
    op.drop_table("classification_nodes")
    op.drop_table("classification_schemes")


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")

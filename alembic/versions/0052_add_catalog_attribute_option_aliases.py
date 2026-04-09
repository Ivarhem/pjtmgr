# -*- coding: utf-8 -*-
"""add catalog attribute option aliases

Revision ID: 0052
Revises: 0051
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0052"
down_revision = "0051"
branch_labels = None
depends_on = None


def _has_table(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "catalog_attribute_option_aliases"):
        return

    op.create_table(
        "catalog_attribute_option_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attribute_option_id", sa.Integer(), nullable=False),
        sa.Column("alias_value", sa.String(length=150), nullable=False),
        sa.Column("normalized_alias", sa.String(length=150), nullable=False),
        sa.Column("match_type", sa.String(length=20), nullable=False, server_default="normalized_exact"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["attribute_option_id"],
            ["catalog_attribute_options.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "attribute_option_id",
            "normalized_alias",
            name="uq_catalog_attribute_option_alias_norm",
        ),
    )
    op.create_index(
        "ix_catalog_attribute_option_aliases_attribute_option_id",
        "catalog_attribute_option_aliases",
        ["attribute_option_id"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_attribute_option_aliases_normalized_alias",
        "catalog_attribute_option_aliases",
        ["normalized_alias"],
        unique=False,
    )


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "catalog_attribute_option_aliases"):
        return

    op.drop_index(
        "ix_catalog_attribute_option_aliases_normalized_alias",
        table_name="catalog_attribute_option_aliases",
    )
    op.drop_index(
        "ix_catalog_attribute_option_aliases_attribute_option_id",
        table_name="catalog_attribute_option_aliases",
    )
    op.drop_table("catalog_attribute_option_aliases")

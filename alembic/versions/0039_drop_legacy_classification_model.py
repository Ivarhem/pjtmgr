# -*- coding: utf-8 -*-
"""Drop legacy classification node model.

Revision ID: 0039
Revises: 0038
Create Date: 2026-03-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def _has_table(conn, table_name: str) -> bool:
    return (
        conn.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = :table_name
                """
            ),
            {"table_name": table_name},
        ).fetchone()
        is not None
    )


def _has_column(conn, table_name: str, column_name: str) -> bool:
    return (
        conn.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = :table_name
                  AND column_name = :column_name
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).fetchone()
        is not None
    )


def _has_index(conn, table_name: str, index_name: str) -> bool:
    return (
        conn.execute(
            sa.text(
                """
                SELECT 1
                FROM pg_indexes
                WHERE tablename = :table_name
                  AND indexname = :index_name
                """
            ),
            {"table_name": table_name, "index_name": index_name},
        ).fetchone()
        is not None
    )


def upgrade() -> None:
    # Legacy classification tables are still referenced by runtime asset/catalog flows.
    # Physical drop is deferred until the application is fully migrated away from:
    # - assets.classification_node_id
    # - product_catalog.classification_node_code/category
    # - classification scheme/node routers and services
    #
    # This revision intentionally acts as a marker so the new attribute-based
    # model can be applied and used first without breaking the running app.
    return


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")

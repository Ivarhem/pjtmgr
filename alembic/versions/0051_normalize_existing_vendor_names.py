# -*- coding: utf-8 -*-
"""normalize existing vendor names

Revision ID: 0051
Revises: 0050
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0051"
down_revision = "0050"
branch_labels = None
depends_on = None


def _has_table(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def _has_column(conn, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspect(conn).get_columns(table_name))


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "catalog_vendor_aliases"):
        return

    aliases = conn.execute(
        sa.text(
            """
            SELECT vendor_canonical, normalized_alias
            FROM catalog_vendor_aliases
            WHERE is_active = TRUE
            ORDER BY vendor_canonical ASC
            """
        )
    ).mappings().all()

    for alias in aliases:
        conn.execute(
            sa.text(
                """
                UPDATE product_catalog
                   SET vendor = :vendor_canonical,
                       normalized_vendor = :vendor_canonical_normalized
                 WHERE normalized_vendor = :normalized_alias
                """
            ),
            {
                "vendor_canonical": alias["vendor_canonical"],
                "vendor_canonical_normalized": _normalize(alias["vendor_canonical"]),
                "normalized_alias": alias["normalized_alias"],
            },
        )
        if _has_table(conn, "assets") and _has_column(conn, "assets", "vendor"):
            conn.execute(
                sa.text(
                    """
                    UPDATE assets
                       SET vendor = :vendor_canonical
                     WHERE LOWER(REGEXP_REPLACE(COALESCE(vendor, ''), '[\\s\\-_./(),]+', '', 'g')) = :normalized_alias
                    """
                ),
                {
                    "vendor_canonical": alias["vendor_canonical"],
                    "normalized_alias": alias["normalized_alias"],
                },
            )
        if _has_table(conn, "assets") and _has_column(conn, "assets", "maintenance_vendor"):
            conn.execute(
                sa.text(
                    """
                    UPDATE assets
                       SET maintenance_vendor = :vendor_canonical
                     WHERE LOWER(REGEXP_REPLACE(COALESCE(maintenance_vendor, ''), '[\\s\\-_./(),]+', '', 'g')) = :normalized_alias
                    """
                ),
                {
                    "vendor_canonical": alias["vendor_canonical"],
                    "normalized_alias": alias["normalized_alias"],
                },
            )


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")


def _normalize(value: str | None) -> str:
    return (
        (value or "")
        .lower()
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .replace(".", "")
        .replace("/", "")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
    )

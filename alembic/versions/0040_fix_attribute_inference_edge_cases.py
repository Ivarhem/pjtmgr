# -*- coding: utf-8 -*-
"""Fix attribute inference edge cases after initial migration.

Revision ID: 0040
Revises: 0039
Create Date: 2026-03-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def _fetch_id(conn, sql: str, **params) -> int | None:
    row = conn.execute(sa.text(sql), params).fetchone()
    return None if row is None else int(row[0])


def _attribute_id(conn, attribute_key: str) -> int | None:
    return _fetch_id(
        conn,
        "SELECT id FROM catalog_attribute_defs WHERE attribute_key = :attribute_key",
        attribute_key=attribute_key,
    )


def _option_id(conn, attribute_key: str, option_key: str) -> int | None:
    return _fetch_id(
        conn,
        """
        SELECT o.id
        FROM catalog_attribute_options o
        JOIN catalog_attribute_defs a ON a.id = o.attribute_id
        WHERE a.attribute_key = :attribute_key
          AND o.option_key = :option_key
        """,
        attribute_key=attribute_key,
        option_key=option_key,
    )


def upgrade() -> None:
    conn = op.get_bind()
    family_attr_id = _attribute_id(conn, "product_family")
    x86_option_id = _option_id(conn, "product_family", "x86_server")
    if family_attr_id is None or x86_option_id is None:
        return

    conn.execute(
        sa.text(
            """
            UPDATE product_catalog_attribute_values v
            SET option_id = :x86_option_id
            FROM product_catalog p
            WHERE v.product_id = p.id
              AND v.attribute_id = :family_attr_id
              AND LOWER(COALESCE(p.vendor, '')) IN ('hpe', 'hp')
              AND (
                  LOWER(COALESCE(p.name, '')) LIKE '%proliant%'
                  OR LOWER(COALESCE(p.name, '')) LIKE '%dl3%'
              )
            """
        ),
        {
            "family_attr_id": family_attr_id,
            "x86_option_id": x86_option_id,
        },
    )


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")

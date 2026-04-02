# -*- coding: utf-8 -*-
"""add product catalog normalized names

Revision ID: 0048
Revises: 0047
Create Date: 2026-03-30
"""

from __future__ import annotations

import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


_SEPARATOR_RE = re.compile(r"[\s\-_./(),]+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z가-힣]+")


def upgrade() -> None:
    op.add_column(
        "product_catalog",
        sa.Column("normalized_vendor", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "product_catalog",
        sa.Column("normalized_name", sa.String(length=400), nullable=True),
    )
    op.create_index(
        "ix_product_catalog_normalized_vendor",
        "product_catalog",
        ["normalized_vendor"],
        unique=False,
    )
    op.create_index(
        "ix_product_catalog_normalized_name",
        "product_catalog",
        ["normalized_name"],
        unique=False,
    )

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, vendor, name FROM product_catalog")).mappings().all()
    for row in rows:
        bind.execute(
            sa.text(
                """
                UPDATE product_catalog
                   SET normalized_vendor = :normalized_vendor,
                       normalized_name = :normalized_name
                 WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "normalized_vendor": _normalize_text(row["vendor"]),
                "normalized_name": _normalize_text(row["name"]),
            },
        )


def downgrade() -> None:
    op.drop_index("ix_product_catalog_normalized_name", table_name="product_catalog")
    op.drop_index("ix_product_catalog_normalized_vendor", table_name="product_catalog")
    op.drop_column("product_catalog", "normalized_name")
    op.drop_column("product_catalog", "normalized_vendor")


def _normalize_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").lower().strip()
    if not normalized:
        return ""
    normalized = _SEPARATOR_RE.sub("", normalized)
    normalized = _NON_ALNUM_RE.sub("", normalized)
    return normalized

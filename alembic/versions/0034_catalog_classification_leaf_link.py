"""Add classification leaf link to product catalog.

Revision ID: 0034
Revises: 0033_classification_level_aliases
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    rows = conn.execute(
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
    return rows is not None


def _has_index(conn, table_name: str, index_name: str) -> bool:
    rows = conn.execute(
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
    return rows is not None


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "product_catalog", "classification_node_code"):
        op.add_column(
            "product_catalog",
            sa.Column("classification_node_code", sa.String(length=50), nullable=True),
        )
    if not _has_index(conn, "product_catalog", "ix_product_catalog_classification_node_code"):
        op.create_index(
            "ix_product_catalog_classification_node_code",
            "product_catalog",
            ["classification_node_code"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_index(conn, "product_catalog", "ix_product_catalog_classification_node_code"):
        op.drop_index(
            "ix_product_catalog_classification_node_code",
            table_name="product_catalog",
        )
    if _has_column(conn, "product_catalog", "classification_node_code"):
        op.drop_column("product_catalog", "classification_node_code")

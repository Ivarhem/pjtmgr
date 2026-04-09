"""Add asset type kind and product catalog metadata fields.

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"


def _has_column(conn, table: str, column: str) -> bool:
    return bool(conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table, "column": column}).scalar())


def _has_index(conn, table: str, index: str) -> bool:
    return bool(conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE tablename = :table AND indexname = :index"
    ), {"table": table, "index": index}).scalar())


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, "asset_type_codes", "kind"):
        op.add_column(
            "asset_type_codes",
            sa.Column("kind", sa.String(length=30), nullable=False, server_default="hardware"),
        )
        conn.execute(sa.text(
            "UPDATE asset_type_codes SET kind = 'software' "
            "WHERE type_key IN ('middleware', 'application')"
        ))
        conn.execute(sa.text(
            "UPDATE asset_type_codes SET kind = 'hardware' WHERE kind IS NULL OR kind = ''"
        ))
        op.alter_column("asset_type_codes", "kind", server_default=None)

    catalog_columns = [
        ("version", sa.String(length=100)),
        ("source_name", sa.String(length=100)),
        ("source_url", sa.String(length=500)),
        ("source_confidence", sa.String(length=30)),
        ("last_verified_at", sa.DateTime()),
        ("verification_status", sa.String(length=30)),
        ("import_batch_id", sa.String(length=100)),
    ]
    for name, col_type in catalog_columns:
        if not _has_column(conn, "product_catalog", name):
            op.add_column("product_catalog", sa.Column(name, col_type, nullable=True))

    if not _has_index(conn, "product_catalog", "ix_product_catalog_import_batch_id"):
        op.create_index(
            "ix_product_catalog_import_batch_id",
            "product_catalog",
            ["import_batch_id"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_index(conn, "product_catalog", "ix_product_catalog_import_batch_id"):
        op.drop_index("ix_product_catalog_import_batch_id", table_name="product_catalog")

    for name in (
        "import_batch_id",
        "verification_status",
        "last_verified_at",
        "source_confidence",
        "source_url",
        "source_name",
        "version",
    ):
        if _has_column(conn, "product_catalog", name):
            op.drop_column("product_catalog", name)

    if _has_column(conn, "asset_type_codes", "kind"):
        op.drop_column("asset_type_codes", "kind")

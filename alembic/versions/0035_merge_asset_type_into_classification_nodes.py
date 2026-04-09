"""Merge asset type metadata into classification nodes.

Revision ID: 0035
Revises: 0034
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0035"
down_revision = "0034"
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
    conn = op.get_bind()

    for column in (
        sa.Column("asset_type_key", sa.String(length=30), nullable=True),
        sa.Column("asset_type_code", sa.String(length=3), nullable=True),
        sa.Column("asset_type_label", sa.String(length=50), nullable=True),
        sa.Column("asset_kind", sa.String(length=30), nullable=True),
        sa.Column("is_catalog_assignable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    ):
        if not _has_column(conn, "classification_nodes", column.name):
            op.add_column("classification_nodes", column)

    if not _has_index(conn, "classification_nodes", "ix_classification_nodes_asset_type_key"):
        op.create_index(
            "ix_classification_nodes_asset_type_key",
            "classification_nodes",
            ["asset_type_key"],
        )

    if _has_table(conn, "asset_type_classification_mappings") and _has_table(conn, "asset_type_codes"):
        conn.execute(
            sa.text(
                """
                UPDATE classification_nodes AS node
                SET
                    asset_type_key = type.type_key,
                    asset_type_code = type.code,
                    asset_type_label = type.label,
                    asset_kind = type.kind,
                    is_catalog_assignable = true
                FROM asset_type_classification_mappings AS map
                JOIN asset_type_codes AS type
                  ON type.type_key = map.asset_type_key
                WHERE node.node_code = map.classification_node_code
                """
            )
        )

    if _has_column(conn, "product_catalog", "asset_type_key"):
        conn.execute(
            sa.text(
                """
                UPDATE product_catalog AS catalog
                SET product_type = COALESCE(node.asset_kind, catalog.product_type)
                FROM classification_nodes AS node
                WHERE catalog.classification_node_code = node.node_code
                  AND node.asset_kind IS NOT NULL
                """
            )
        )

    conn.execute(
        sa.text(
            """
            UPDATE classification_nodes
            SET is_catalog_assignable = true
            WHERE asset_type_key IS NOT NULL
            """
        )
    )

    if _has_index(conn, "product_catalog", "ix_product_catalog_asset_type_key"):
        op.drop_index("ix_product_catalog_asset_type_key", table_name="product_catalog")
    if _has_column(conn, "product_catalog", "asset_type_key"):
        op.drop_column("product_catalog", "asset_type_key")

    if _has_table(conn, "asset_type_classification_mappings"):
        op.drop_table("asset_type_classification_mappings")
    if _has_table(conn, "asset_type_codes"):
        op.drop_table("asset_type_codes")

    conn.execute(
        sa.text(
            """
            ALTER TABLE classification_nodes
            ALTER COLUMN is_catalog_assignable DROP DEFAULT
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "asset_type_codes"):
        op.create_table(
            "asset_type_codes",
            sa.Column("type_key", sa.String(length=30), primary_key=True),
            sa.Column("code", sa.String(length=3), nullable=False, unique=True),
            sa.Column("label", sa.String(length=50), nullable=False),
            sa.Column("kind", sa.String(length=30), nullable=False, server_default="hardware"),
            sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        )
    if not _has_table(conn, "asset_type_classification_mappings"):
        op.create_table(
            "asset_type_classification_mappings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("asset_type_key", sa.String(length=30), nullable=False),
            sa.Column("classification_node_code", sa.String(length=50), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.ForeignKeyConstraint(["asset_type_key"], ["asset_type_codes.type_key"], ondelete="CASCADE"),
            sa.UniqueConstraint("asset_type_key", "classification_node_code", name="uq_asset_type_classification_mapping"),
        )

    if not _has_column(conn, "product_catalog", "asset_type_key"):
        op.add_column("product_catalog", sa.Column("asset_type_key", sa.String(length=30), nullable=True))
        op.create_index("ix_product_catalog_asset_type_key", "product_catalog", ["asset_type_key"])

    if _has_index(conn, "classification_nodes", "ix_classification_nodes_asset_type_key"):
        op.drop_index("ix_classification_nodes_asset_type_key", table_name="classification_nodes")
    for column_name in (
        "is_catalog_assignable",
        "asset_kind",
        "asset_type_label",
        "asset_type_code",
        "asset_type_key",
    ):
        if _has_column(conn, "classification_nodes", column_name):
            op.drop_column("classification_nodes", column_name)

"""Add catalog attribute and classification layout model.

Revision ID: 0036
Revises: 0035
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0036"
down_revision = "0035"
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


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "catalog_attribute_defs"):
        op.create_table(
            "catalog_attribute_defs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("attribute_key", sa.String(length=50), nullable=False),
            sa.Column("label", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("value_type", sa.String(length=20), nullable=False),
            sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_display_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_displayable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("multi_value", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("attribute_key", name="uq_catalog_attribute_def_key"),
        )
        op.create_index(
            "ix_catalog_attribute_defs_attribute_key",
            "catalog_attribute_defs",
            ["attribute_key"],
            unique=False,
        )

    if not _has_table(conn, "catalog_attribute_options"):
        op.create_table(
            "catalog_attribute_options",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("attribute_id", sa.Integer(), nullable=False),
            sa.Column("option_key", sa.String(length=50), nullable=False),
            sa.Column("label", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["attribute_id"],
                ["catalog_attribute_defs.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("attribute_id", "option_key", name="uq_catalog_attribute_option_key"),
        )
        op.create_index(
            "ix_catalog_attribute_options_attribute_id",
            "catalog_attribute_options",
            ["attribute_id"],
            unique=False,
        )

    if not _has_table(conn, "classification_layouts"):
        op.create_table(
            "classification_layouts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scope_type", sa.String(length=20), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("depth_count", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["project_id"],
                ["contract_periods.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_classification_layouts_scope_type",
            "classification_layouts",
            ["scope_type"],
            unique=False,
        )
        op.create_index(
            "ix_classification_layouts_project_id",
            "classification_layouts",
            ["project_id"],
            unique=False,
        )

    if not _has_table(conn, "classification_layout_levels"):
        op.create_table(
            "classification_layout_levels",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("layout_id", sa.Integer(), nullable=False),
            sa.Column("level_no", sa.Integer(), nullable=False),
            sa.Column("alias", sa.String(length=100), nullable=False),
            sa.Column("joiner", sa.String(length=20), nullable=True),
            sa.Column("prefix_mode", sa.String(length=30), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["layout_id"],
                ["classification_layouts.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("layout_id", "level_no", name="uq_classification_layout_level"),
        )
        op.create_index(
            "ix_classification_layout_levels_layout_id",
            "classification_layout_levels",
            ["layout_id"],
            unique=False,
        )

    if not _has_table(conn, "classification_layout_level_keys"):
        op.create_table(
            "classification_layout_level_keys",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("level_id", sa.Integer(), nullable=False),
            sa.Column("attribute_id", sa.Integer(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["level_id"],
                ["classification_layout_levels.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["attribute_id"],
                ["catalog_attribute_defs.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("level_id", "attribute_id", name="uq_classification_layout_level_key"),
        )
        op.create_index(
            "ix_classification_layout_level_keys_level_id",
            "classification_layout_level_keys",
            ["level_id"],
            unique=False,
        )
        op.create_index(
            "ix_classification_layout_level_keys_attribute_id",
            "classification_layout_level_keys",
            ["attribute_id"],
            unique=False,
        )

    if not _has_table(conn, "asset_identity_rules"):
        op.create_table(
            "asset_identity_rules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("domain_option_id", sa.Integer(), nullable=True),
            sa.Column("imp_type_option_id", sa.Integer(), nullable=True),
            sa.Column("product_family_option_id", sa.Integer(), nullable=True),
            sa.Column("platform_option_id", sa.Integer(), nullable=True),
            sa.Column("asset_type_code", sa.String(length=20), nullable=False),
            sa.Column("asset_type_label", sa.String(length=100), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["domain_option_id"],
                ["catalog_attribute_options.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["imp_type_option_id"],
                ["catalog_attribute_options.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["product_family_option_id"],
                ["catalog_attribute_options.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["platform_option_id"],
                ["catalog_attribute_options.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_asset_identity_rules_domain_option_id", "asset_identity_rules", ["domain_option_id"], unique=False)
        op.create_index("ix_asset_identity_rules_imp_type_option_id", "asset_identity_rules", ["imp_type_option_id"], unique=False)
        op.create_index("ix_asset_identity_rules_product_family_option_id", "asset_identity_rules", ["product_family_option_id"], unique=False)
        op.create_index("ix_asset_identity_rules_platform_option_id", "asset_identity_rules", ["platform_option_id"], unique=False)
        op.create_index("ix_asset_identity_rules_priority", "asset_identity_rules", ["priority"], unique=False)

    if not _has_table(conn, "product_catalog_attribute_values"):
        op.create_table(
            "product_catalog_attribute_values",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("attribute_id", sa.Integer(), nullable=False),
            sa.Column("option_id", sa.Integer(), nullable=True),
            sa.Column("raw_value", sa.String(length=255), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["product_id"],
                ["product_catalog.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["attribute_id"],
                ["catalog_attribute_defs.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["option_id"],
                ["catalog_attribute_options.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("product_id", "attribute_id", name="uq_product_catalog_attribute_value"),
        )
        op.create_index(
            "ix_product_catalog_attribute_values_product_id",
            "product_catalog_attribute_values",
            ["product_id"],
            unique=False,
        )
        op.create_index(
            "ix_product_catalog_attribute_values_attribute_id",
            "product_catalog_attribute_values",
            ["attribute_id"],
            unique=False,
        )
        op.create_index(
            "ix_product_catalog_attribute_values_option_id",
            "product_catalog_attribute_values",
            ["option_id"],
            unique=False,
        )

    if not _has_column(conn, "contract_periods", "classification_layout_id"):
        op.add_column(
            "contract_periods",
            sa.Column("classification_layout_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_contract_periods_classification_layout_id",
            "contract_periods",
            "classification_layouts",
            ["classification_layout_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index(
            "ix_contract_periods_classification_layout_id",
            "contract_periods",
            ["classification_layout_id"],
            unique=False,
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_column(conn, "contract_periods", "classification_layout_id"):
        op.drop_index("ix_contract_periods_classification_layout_id", table_name="contract_periods")
        op.drop_constraint("fk_contract_periods_classification_layout_id", "contract_periods", type_="foreignkey")
        op.drop_column("contract_periods", "classification_layout_id")

    if _has_table(conn, "product_catalog_attribute_values"):
        op.drop_index("ix_product_catalog_attribute_values_option_id", table_name="product_catalog_attribute_values")
        op.drop_index("ix_product_catalog_attribute_values_attribute_id", table_name="product_catalog_attribute_values")
        op.drop_index("ix_product_catalog_attribute_values_product_id", table_name="product_catalog_attribute_values")
        op.drop_table("product_catalog_attribute_values")

    if _has_table(conn, "asset_identity_rules"):
        op.drop_index("ix_asset_identity_rules_priority", table_name="asset_identity_rules")
        op.drop_index("ix_asset_identity_rules_platform_option_id", table_name="asset_identity_rules")
        op.drop_index("ix_asset_identity_rules_product_family_option_id", table_name="asset_identity_rules")
        op.drop_index("ix_asset_identity_rules_imp_type_option_id", table_name="asset_identity_rules")
        op.drop_index("ix_asset_identity_rules_domain_option_id", table_name="asset_identity_rules")
        op.drop_table("asset_identity_rules")

    if _has_table(conn, "classification_layout_level_keys"):
        op.drop_index("ix_classification_layout_level_keys_attribute_id", table_name="classification_layout_level_keys")
        op.drop_index("ix_classification_layout_level_keys_level_id", table_name="classification_layout_level_keys")
        op.drop_table("classification_layout_level_keys")

    if _has_table(conn, "classification_layout_levels"):
        op.drop_index("ix_classification_layout_levels_layout_id", table_name="classification_layout_levels")
        op.drop_table("classification_layout_levels")

    if _has_table(conn, "classification_layouts"):
        op.drop_index("ix_classification_layouts_project_id", table_name="classification_layouts")
        op.drop_index("ix_classification_layouts_scope_type", table_name="classification_layouts")
        op.drop_table("classification_layouts")

    if _has_table(conn, "catalog_attribute_options"):
        op.drop_index("ix_catalog_attribute_options_attribute_id", table_name="catalog_attribute_options")
        op.drop_table("catalog_attribute_options")

    if _has_table(conn, "catalog_attribute_defs"):
        op.drop_index("ix_catalog_attribute_defs_attribute_key", table_name="catalog_attribute_defs")
        op.drop_table("catalog_attribute_defs")

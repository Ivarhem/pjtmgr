"""add asset type classification mappings

Revision ID: 0027
Revises: 0026
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("asset_type_classification_mappings"):
        op.create_table(
            "asset_type_classification_mappings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("asset_type_key", sa.String(length=30), nullable=False),
            sa.Column("classification_node_code", sa.String(length=50), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["asset_type_key"], ["asset_type_codes.type_key"], ondelete="CASCADE"),
            sa.UniqueConstraint("asset_type_key", "classification_node_code", name="uq_asset_type_classification_mapping"),
        )

    indexes = {idx["name"] for idx in inspector.get_indexes("asset_type_classification_mappings")}
    if op.f("ix_asset_type_classification_mappings_asset_type_key") not in indexes:
        op.create_index(op.f("ix_asset_type_classification_mappings_asset_type_key"), "asset_type_classification_mappings", ["asset_type_key"], unique=False)
    if op.f("ix_asset_type_classification_mappings_classification_node_code") not in indexes:
        op.create_index(op.f("ix_asset_type_classification_mappings_classification_node_code"), "asset_type_classification_mappings", ["classification_node_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_type_classification_mappings_classification_node_code"), table_name="asset_type_classification_mappings")
    op.drop_index(op.f("ix_asset_type_classification_mappings_asset_type_key"), table_name="asset_type_classification_mappings")
    op.drop_table("asset_type_classification_mappings")

"""add product catalog family fields

Revision ID: 0077
Revises: 0076
Create Date: 2026-04-24 16:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0077"
down_revision = "0076"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("product_catalog", sa.Column("model_family", sa.String(length=255), nullable=True))
    op.add_column("product_catalog", sa.Column("is_family_level", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("ix_product_catalog_model_family", "product_catalog", ["model_family"], unique=False)

    op.execute(
        """
        UPDATE product_catalog
        SET is_family_level = false
        WHERE is_family_level IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_product_catalog_model_family", table_name="product_catalog")
    op.drop_column("product_catalog", "is_family_level")
    op.drop_column("product_catalog", "model_family")

"""add asset project and customer numbers

Revision ID: 0023
Revises: 0022
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("project_asset_number", sa.String(length=100), nullable=True))
    op.add_column("assets", sa.Column("customer_asset_number", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_assets_project_asset_number"), "assets", ["project_asset_number"], unique=False)
    op.create_index(op.f("ix_assets_customer_asset_number"), "assets", ["customer_asset_number"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_assets_customer_asset_number"), table_name="assets")
    op.drop_index(op.f("ix_assets_project_asset_number"), table_name="assets")
    op.drop_column("assets", "customer_asset_number")
    op.drop_column("assets", "project_asset_number")

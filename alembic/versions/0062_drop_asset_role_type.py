"""Drop role_type column from asset_roles table.

Revision ID: 0062
Revises: 0061
"""
from alembic import op
import sqlalchemy as sa

revision = "0062"
down_revision = "0061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_asset_roles_role_type", table_name="asset_roles")
    op.drop_column("asset_roles", "role_type")


def downgrade() -> None:
    op.add_column(
        "asset_roles",
        sa.Column("role_type", sa.String(100), nullable=True),
    )
    op.create_index("ix_asset_roles_role_type", "asset_roles", ["role_type"])

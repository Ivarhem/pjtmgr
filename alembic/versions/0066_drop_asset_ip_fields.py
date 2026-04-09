"""Drop service_ip and mgmt_ip from assets table.

These fields are replaced by AssetIP (via asset_interface FK).

Revision ID: 0066
Revises: 0065
"""
from alembic import op
import sqlalchemy as sa

revision = "0066"
down_revision = "0065"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("assets", "service_ip")
    op.drop_column("assets", "mgmt_ip")


def downgrade() -> None:
    op.add_column("assets", sa.Column("mgmt_ip", sa.String(64), nullable=True))
    op.add_column("assets", sa.Column("service_ip", sa.String(64), nullable=True))

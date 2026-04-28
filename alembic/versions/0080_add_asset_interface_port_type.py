"""add asset interface port type

Revision ID: 0080
Revises: 0079
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0080"
down_revision = "0079"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("asset_interfaces", sa.Column("port_type", sa.String(length=30), nullable=True))

def downgrade() -> None:
    op.drop_column("asset_interfaces", "port_type")

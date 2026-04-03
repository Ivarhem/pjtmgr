"""add similar_count to product_catalog

Revision ID: 0060
Revises: 0059
"""
from alembic import op
import sqlalchemy as sa

revision = "0060"
down_revision = "0059"


def upgrade() -> None:
    op.add_column("product_catalog", sa.Column("similar_count", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("product_catalog", "similar_count")

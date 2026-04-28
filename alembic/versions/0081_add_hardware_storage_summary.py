"""add hardware storage summary

Revision ID: 0081
Revises: 0080
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0081"
down_revision = "0080"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("hardware_specs", sa.Column("storage_summary", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("hardware_specs", "storage_summary")

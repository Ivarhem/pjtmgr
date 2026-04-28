"""add hardware power summary

Revision ID: 0082
Revises: 0081
Create Date: 2026-04-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0082"
down_revision = "0081"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("hardware_specs", sa.Column("power_summary", sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column("hardware_specs", "power_summary")

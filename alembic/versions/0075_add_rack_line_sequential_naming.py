"""add rack line sequential naming option

Revision ID: 0075
Revises: 0074
Create Date: 2026-04-21 12:59:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0075"
down_revision = "0074"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rack_lines", sa.Column("sequential_naming", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.alter_column("rack_lines", "sequential_naming", server_default=None)


def downgrade() -> None:
    op.drop_column("rack_lines", "sequential_naming")

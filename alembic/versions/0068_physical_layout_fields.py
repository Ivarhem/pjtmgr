"""Add physical layout fields: racks_per_row, sort_order, rack units, label base.

Revision ID: 0068
Revises: 0067
"""
from alembic import op
import sqlalchemy as sa

revision = "0068"
down_revision = "0067"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rooms", sa.Column("racks_per_row", sa.Integer(), nullable=False, server_default="6"))
    op.add_column("racks", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("assets", sa.Column("rack_start_unit", sa.Integer(), nullable=True))
    op.add_column("assets", sa.Column("rack_end_unit", sa.Integer(), nullable=True))
    op.add_column(
        "contract_periods",
        sa.Column("rack_label_base", sa.String(10), nullable=False, server_default="start"),
    )


def downgrade() -> None:
    op.drop_column("contract_periods", "rack_label_base")
    op.drop_column("assets", "rack_end_unit")
    op.drop_column("assets", "rack_start_unit")
    op.drop_column("racks", "sort_order")
    op.drop_column("rooms", "racks_per_row")

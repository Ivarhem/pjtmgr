"""add coordinate-defined rack line fields

Revision ID: 0073_add_rack_line_coordinates
Revises: 0072_port_map_media_and_connectors
Create Date: 2026-04-17 17:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0073"
down_revision = "0072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_rack_lines_room_col", "rack_lines", type_="unique")
    op.add_column("rack_lines", sa.Column("start_col", sa.Integer(), nullable=True))
    op.add_column("rack_lines", sa.Column("start_row", sa.Integer(), nullable=True))
    op.add_column("rack_lines", sa.Column("end_col", sa.Integer(), nullable=True))
    op.add_column("rack_lines", sa.Column("end_row", sa.Integer(), nullable=True))
    op.add_column("rack_lines", sa.Column("direction", sa.String(length=20), nullable=True))
    op.alter_column("rack_lines", "col_index", existing_type=sa.Integer(), nullable=True)

    op.execute("""
        UPDATE rack_lines
        SET start_col = col_index,
            end_col = col_index,
            start_row = 0,
            end_row = GREATEST(COALESCE(slot_count, 1) - 1, 0),
            direction = CASE WHEN col_index IS NOT NULL AND col_index >= 0 THEN 'vertical' ELSE NULL END
        WHERE col_index IS NOT NULL AND col_index >= 0
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE rack_lines
        SET col_index = COALESCE(col_index, start_col)
        WHERE col_index IS NULL AND start_col IS NOT NULL
    """)
    op.alter_column("rack_lines", "col_index", existing_type=sa.Integer(), nullable=False)
    op.drop_column("rack_lines", "direction")
    op.drop_column("rack_lines", "end_row")
    op.drop_column("rack_lines", "end_col")
    op.drop_column("rack_lines", "start_row")
    op.drop_column("rack_lines", "start_col")
    op.create_unique_constraint("uq_rack_lines_room_col", "rack_lines", ["room_id", "col_index"])

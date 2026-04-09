"""add asset physical layout refs

Revision ID: 0025
Revises: 0024
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("center_id", sa.Integer(), nullable=True))
    op.add_column("assets", sa.Column("room_id", sa.Integer(), nullable=True))
    op.add_column("assets", sa.Column("rack_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_assets_center_id"), "assets", ["center_id"], unique=False)
    op.create_index(op.f("ix_assets_room_id"), "assets", ["room_id"], unique=False)
    op.create_index(op.f("ix_assets_rack_id"), "assets", ["rack_id"], unique=False)
    op.create_foreign_key(None, "assets", "centers", ["center_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(None, "assets", "rooms", ["room_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(None, "assets", "racks", ["rack_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint(op.f("assets_rack_id_fkey"), "assets", type_="foreignkey")
    op.drop_constraint(op.f("assets_room_id_fkey"), "assets", type_="foreignkey")
    op.drop_constraint(op.f("assets_center_id_fkey"), "assets", type_="foreignkey")
    op.drop_index(op.f("ix_assets_rack_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_room_id"), table_name="assets")
    op.drop_index(op.f("ix_assets_center_id"), table_name="assets")
    op.drop_column("assets", "rack_id")
    op.drop_column("assets", "room_id")
    op.drop_column("assets", "center_id")

"""add centers rooms racks tables

Revision ID: 0024
Revises: 0023
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "centers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("center_code", sa.String(length=50), nullable=False),
        sa.Column("center_name", sa.String(length=200), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_id", "center_code", name="uq_centers_partner_code"),
    )
    op.create_index(op.f("ix_centers_partner_id"), "centers", ["partner_id"], unique=False)
    op.create_index(op.f("ix_centers_center_code"), "centers", ["center_code"], unique=False)

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("center_id", sa.Integer(), nullable=False),
        sa.Column("room_code", sa.String(length=50), nullable=False),
        sa.Column("room_name", sa.String(length=200), nullable=False),
        sa.Column("floor", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["center_id"], ["centers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("center_id", "room_code", name="uq_rooms_center_code"),
    )
    op.create_index(op.f("ix_rooms_center_id"), "rooms", ["center_id"], unique=False)
    op.create_index(op.f("ix_rooms_room_code"), "rooms", ["room_code"], unique=False)

    op.create_table(
        "racks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("rack_code", sa.String(length=50), nullable=False),
        sa.Column("rack_name", sa.String(length=200), nullable=True),
        sa.Column("total_units", sa.Integer(), nullable=False, server_default="42"),
        sa.Column("location_detail", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "rack_code", name="uq_racks_room_code"),
    )
    op.create_index(op.f("ix_racks_room_id"), "racks", ["room_id"], unique=False)
    op.create_index(op.f("ix_racks_rack_code"), "racks", ["rack_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_racks_rack_code"), table_name="racks")
    op.drop_index(op.f("ix_racks_room_id"), table_name="racks")
    op.drop_table("racks")
    op.drop_index(op.f("ix_rooms_room_code"), table_name="rooms")
    op.drop_index(op.f("ix_rooms_center_id"), table_name="rooms")
    op.drop_table("rooms")
    op.drop_index(op.f("ix_centers_center_code"), table_name="centers")
    op.drop_index(op.f("ix_centers_partner_id"), table_name="centers")
    op.drop_table("centers")

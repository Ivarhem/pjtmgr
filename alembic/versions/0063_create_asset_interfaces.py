"""Create asset_interfaces table.

Revision ID: 0063
Revises: 0062
"""
from alembic import op
import sqlalchemy as sa

revision = "0063"
down_revision = "0062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_interfaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("asset_interfaces.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("hw_interface_id", sa.Integer(), sa.ForeignKey("hardware_interfaces.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("if_type", sa.String(30), nullable=False, server_default="physical"),
        sa.Column("slot", sa.String(30), nullable=True),
        sa.Column("slot_position", sa.Integer(), nullable=True),
        sa.Column("speed", sa.String(20), nullable=True),
        sa.Column("media_type", sa.String(30), nullable=True),
        sa.Column("mac_address", sa.String(17), nullable=True),
        sa.Column("admin_status", sa.String(20), nullable=False, server_default="up"),
        sa.Column("oper_status", sa.String(20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("asset_id", "name", name="uq_asset_interface_name"),
        sa.CheckConstraint("parent_id != id", name="ck_no_self_parent"),
    )


def downgrade() -> None:
    op.drop_table("asset_interfaces")

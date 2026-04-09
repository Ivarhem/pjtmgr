"""Add asset events table.

Revision ID: 0020
Revises: 0019
"""
from alembic import op
import sqlalchemy as sa


revision = "0020"
down_revision = "0019"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "asset_events" not in inspector.get_table_names():
        op.create_table(
            "asset_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("asset_id", sa.Integer(), nullable=True),
            sa.Column("related_asset_id", sa.Integer(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("summary", sa.String(length=500), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("asset_code_snapshot", sa.String(length=50), nullable=True),
            sa.Column("asset_name_snapshot", sa.String(length=255), nullable=True),
            sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["related_asset_id"], ["assets.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("asset_events")}
    if "ix_asset_events_asset_id" not in existing_indexes:
        op.create_index("ix_asset_events_asset_id", "asset_events", ["asset_id"])
    if "ix_asset_events_related_asset_id" not in existing_indexes:
        op.create_index("ix_asset_events_related_asset_id", "asset_events", ["related_asset_id"])
    if "ix_asset_events_created_by_user_id" not in existing_indexes:
        op.create_index("ix_asset_events_created_by_user_id", "asset_events", ["created_by_user_id"])
    if "ix_asset_events_event_type" not in existing_indexes:
        op.create_index("ix_asset_events_event_type", "asset_events", ["event_type"])
    if "ix_asset_events_occurred_at" not in existing_indexes:
        op.create_index("ix_asset_events_occurred_at", "asset_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_asset_events_occurred_at", table_name="asset_events")
    op.drop_index("ix_asset_events_event_type", table_name="asset_events")
    op.drop_index("ix_asset_events_created_by_user_id", table_name="asset_events")
    op.drop_index("ix_asset_events_related_asset_id", table_name="asset_events")
    op.drop_index("ix_asset_events_asset_id", table_name="asset_events")
    op.drop_table("asset_events")

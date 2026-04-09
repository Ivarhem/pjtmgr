"""add asset related partners

Revision ID: 0021
Revises: 0020
Create Date: 2026-03-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "asset_related_partners" not in inspector.get_table_names():
        op.create_table(
            "asset_related_partners",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("partner_id", sa.Integer(), nullable=False),
            sa.Column("relation_type", sa.String(length=50), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("valid_from", sa.Date(), nullable=True),
            sa.Column("valid_to", sa.Date(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["partner_id"], ["partners.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("asset_related_partners")}
    if "ix_asset_related_partners_asset_id" not in existing_indexes:
        op.create_index(
            op.f("ix_asset_related_partners_asset_id"),
            "asset_related_partners",
            ["asset_id"],
            unique=False,
        )
    if "ix_asset_related_partners_partner_id" not in existing_indexes:
        op.create_index(
            op.f("ix_asset_related_partners_partner_id"),
            "asset_related_partners",
            ["partner_id"],
            unique=False,
        )
    if "ix_asset_related_partners_relation_type" not in existing_indexes:
        op.create_index(
            op.f("ix_asset_related_partners_relation_type"),
            "asset_related_partners",
            ["relation_type"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_related_partners_relation_type"), table_name="asset_related_partners")
    op.drop_index(op.f("ix_asset_related_partners_partner_id"), table_name="asset_related_partners")
    op.drop_index(op.f("ix_asset_related_partners_asset_id"), table_name="asset_related_partners")
    op.drop_table("asset_related_partners")

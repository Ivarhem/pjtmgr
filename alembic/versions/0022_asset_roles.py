"""add asset roles and assignments

Revision ID: 0022
Revises: 0021
Create Date: 2026-03-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "asset_roles" not in inspector.get_table_names():
        op.create_table(
            "asset_roles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("partner_id", sa.Integer(), nullable=False),
            sa.Column("contract_period_id", sa.Integer(), nullable=True),
            sa.Column("role_name", sa.String(length=255), nullable=False),
            sa.Column("role_type", sa.String(length=100), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["contract_period_id"], ["contract_periods.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["partner_id"], ["partners.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    existing_role_indexes = {idx["name"] for idx in inspector.get_indexes("asset_roles")}
    for index_name, columns in [
        ("ix_asset_roles_partner_id", ["partner_id"]),
        ("ix_asset_roles_contract_period_id", ["contract_period_id"]),
        ("ix_asset_roles_role_name", ["role_name"]),
        ("ix_asset_roles_role_type", ["role_type"]),
        ("ix_asset_roles_status", ["status"]),
    ]:
        if index_name not in existing_role_indexes:
            op.create_index(index_name, "asset_roles", columns)

    if "asset_role_assignments" not in inspector.get_table_names():
        op.create_table(
            "asset_role_assignments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("asset_role_id", sa.Integer(), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("assignment_type", sa.String(length=50), nullable=False),
            sa.Column("valid_from", sa.Date(), nullable=True),
            sa.Column("valid_to", sa.Date(), nullable=True),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["asset_role_id"], ["asset_roles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    existing_assignment_indexes = {idx["name"] for idx in inspector.get_indexes("asset_role_assignments")}
    for index_name, columns in [
        ("ix_asset_role_assignments_asset_role_id", ["asset_role_id"]),
        ("ix_asset_role_assignments_asset_id", ["asset_id"]),
    ]:
        if index_name not in existing_assignment_indexes:
            op.create_index(index_name, "asset_role_assignments", columns)


def downgrade() -> None:
    op.drop_index("ix_asset_role_assignments_asset_id", table_name="asset_role_assignments")
    op.drop_index("ix_asset_role_assignments_asset_role_id", table_name="asset_role_assignments")
    op.drop_table("asset_role_assignments")
    op.drop_index("ix_asset_roles_status", table_name="asset_roles")
    op.drop_index("ix_asset_roles_role_type", table_name="asset_roles")
    op.drop_index("ix_asset_roles_role_name", table_name="asset_roles")
    op.drop_index("ix_asset_roles_contract_period_id", table_name="asset_roles")
    op.drop_index("ix_asset_roles_partner_id", table_name="asset_roles")
    op.drop_table("asset_roles")

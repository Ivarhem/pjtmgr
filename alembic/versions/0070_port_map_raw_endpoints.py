"""add raw endpoint fields to port maps

Revision ID: 0070
Revises: 0069
Create Date: 2026-04-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0070"
down_revision: str = "0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("port_maps", sa.Column("src_asset_name_raw", sa.String(length=255), nullable=True))
    op.add_column("port_maps", sa.Column("src_interface_name_raw", sa.String(length=100), nullable=True))
    op.add_column("port_maps", sa.Column("dst_asset_name_raw", sa.String(length=255), nullable=True))
    op.add_column("port_maps", sa.Column("dst_interface_name_raw", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("port_maps", "dst_interface_name_raw")
    op.drop_column("port_maps", "dst_asset_name_raw")
    op.drop_column("port_maps", "src_interface_name_raw")
    op.drop_column("port_maps", "src_asset_name_raw")

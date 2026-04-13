"""add port map media category and connector types

Revision ID: 0072
Revises: 0071
Create Date: 2026-04-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0072"
down_revision: str = "0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("port_maps", sa.Column("media_category", sa.String(length=30), nullable=True))
    op.add_column("port_maps", sa.Column("src_connector_type", sa.String(length=50), nullable=True))
    op.add_column("port_maps", sa.Column("dst_connector_type", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("port_maps", "dst_connector_type")
    op.drop_column("port_maps", "src_connector_type")
    op.drop_column("port_maps", "media_category")

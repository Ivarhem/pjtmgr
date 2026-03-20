"""Asset restructure: project_assets, asset_code, asset_relations.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect, text

# revision identifiers
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return name in inspector.get_table_names()


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    # -- project_assets (N:M link) --
    if not _table_exists("project_assets"):
        op.create_table(
            "project_assets",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("projects.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "asset_id",
                sa.Integer(),
                sa.ForeignKey("assets.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("role", sa.String(100), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("project_id", "asset_id", name="uq_project_asset"),
        )

        # Backfill: copy existing Asset.project_id → project_assets
        op.get_bind().execute(
            text(
                """
                INSERT INTO project_assets (project_id, asset_id, created_at, updated_at)
                SELECT project_id, id, now(), now()
                FROM assets
                WHERE project_id IS NOT NULL
                ON CONFLICT DO NOTHING
                """
            )
        )

    # -- assets.asset_code --
    if _table_exists("assets") and not _column_exists("assets", "asset_code"):
        op.add_column("assets", sa.Column("asset_code", sa.String(50), nullable=True))
        op.create_index("ix_assets_asset_code", "assets", ["asset_code"], unique=True)

    # -- asset_relations --
    if not _table_exists("asset_relations"):
        op.create_table(
            "asset_relations",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column(
                "src_asset_id",
                sa.Integer(),
                sa.ForeignKey("assets.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "dst_asset_id",
                sa.Integer(),
                sa.ForeignKey("assets.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("relation_type", sa.String(50), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
            sa.CheckConstraint(
                "src_asset_id != dst_asset_id", name="ck_no_self_relation"
            ),
        )


def downgrade() -> None:
    op.drop_table("asset_relations")
    if _column_exists("assets", "asset_code"):
        op.drop_index("ix_assets_asset_code", table_name="assets")
        op.drop_column("assets", "asset_code")
    op.drop_table("project_assets")

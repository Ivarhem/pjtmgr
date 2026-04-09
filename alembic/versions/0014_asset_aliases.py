"""Add asset_aliases table.

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'asset_aliases'"
    ))
    if result.scalar():
        return
    op.create_table(
        "asset_aliases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("alias_name", sa.String(255), nullable=False, unique=True),
        sa.Column("alias_type", sa.String(30), nullable=False),
        sa.Column("source_partner_id", sa.Integer(), sa.ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("source_text", sa.String(200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("asset_aliases")

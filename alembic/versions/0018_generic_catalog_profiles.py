"""Add generic catalog profiles for service-like product kinds.

Revision ID: 0018
Revises: 0017
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"


def _has_table(conn, table: str) -> bool:
    return bool(conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = :table"
    ), {"table": table}).scalar())


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "generic_catalog_profiles"):
        op.create_table(
            "generic_catalog_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("owner_scope", sa.String(length=100), nullable=True),
            sa.Column("service_level", sa.String(length=50), nullable=True),
            sa.Column("criticality", sa.String(length=50), nullable=True),
            sa.Column("exposure_scope", sa.String(length=50), nullable=True),
            sa.Column("data_classification", sa.String(length=50), nullable=True),
            sa.Column("default_runtime", sa.String(length=100), nullable=True),
            sa.Column("summary_note", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "generic_catalog_profiles"):
        op.drop_table("generic_catalog_profiles")

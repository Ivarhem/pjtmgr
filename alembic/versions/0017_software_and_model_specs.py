"""Add software_specs and model_specs tables.

Revision ID: 0017
Revises: 0016
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"


def _has_table(conn, table: str) -> bool:
    return bool(conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table"
    ), {"table": table}).scalar())


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, "software_specs"):
        op.create_table(
            "software_specs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("edition", sa.String(length=100), nullable=True),
            sa.Column("license_type", sa.String(length=50), nullable=True),
            sa.Column("license_unit", sa.String(length=50), nullable=True),
            sa.Column("deployment_type", sa.String(length=50), nullable=True),
            sa.Column("runtime_env", sa.String(length=100), nullable=True),
            sa.Column("support_vendor", sa.String(length=100), nullable=True),
            sa.Column("architecture_note", sa.Text(), nullable=True),
        )

    if not _has_table(conn, "model_specs"):
        op.create_table(
            "model_specs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("provider", sa.String(length=100), nullable=True),
            sa.Column("model_family", sa.String(length=100), nullable=True),
            sa.Column("modality", sa.String(length=50), nullable=True),
            sa.Column("deployment_scope", sa.String(length=50), nullable=True),
            sa.Column("context_window", sa.Integer(), nullable=True),
            sa.Column("endpoint_format", sa.String(length=100), nullable=True),
            sa.Column("capability_note", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "model_specs"):
        op.drop_table("model_specs")
    if _has_table(conn, "software_specs"):
        op.drop_table("software_specs")

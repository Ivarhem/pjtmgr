"""Create product_catalog, hardware_specs, hardware_interfaces tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_catalog",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("vendor", sa.String(100), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("product_type", sa.String(20), nullable=False, server_default="hardware"),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("eos_date", sa.Date, nullable=True),
        sa.Column("eosl_date", sa.Date, nullable=True),
        sa.Column("eosl_note", sa.Text, nullable=True),
        sa.Column("reference_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("vendor", "name", name="uq_product_catalog_vendor_name"),
    )

    op.create_table(
        "hardware_specs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("size_unit", sa.Integer, nullable=True),
        sa.Column("width_mm", sa.Integer, nullable=True),
        sa.Column("height_mm", sa.Integer, nullable=True),
        sa.Column("depth_mm", sa.Integer, nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("power_count", sa.Integer, nullable=True),
        sa.Column("power_type", sa.String(50), nullable=True),
        sa.Column("power_watt", sa.Integer, nullable=True),
        sa.Column("cpu_summary", sa.Text, nullable=True),
        sa.Column("memory_summary", sa.Text, nullable=True),
        sa.Column("throughput_summary", sa.Text, nullable=True),
        sa.Column("os_firmware", sa.Text, nullable=True),
        sa.Column("spec_url", sa.String(500), nullable=True),
    )

    op.create_table(
        "hardware_interfaces",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer, sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("interface_type", sa.String(30), nullable=False),
        sa.Column("speed", sa.String(20), nullable=True),
        sa.Column("count", sa.Integer, nullable=False),
        sa.Column("connector_type", sa.String(30), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("hardware_interfaces")
    op.drop_table("hardware_specs")
    op.drop_table("product_catalog")

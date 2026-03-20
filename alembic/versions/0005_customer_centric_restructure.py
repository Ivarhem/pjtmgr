"""Customer-centric restructure: move asset/subnet/portmap/policy ownership
from project to customer.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def _index_exists(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table))


def _fk_exists(table: str, fk_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return any(
        fk["name"] == fk_name for fk in inspector.get_foreign_keys(table)
    )


def upgrade() -> None:
    conn = op.get_bind()

    # ── Pre-check: all projects must have customer_id ──
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM projects WHERE customer_id IS NULL")
    )
    null_count = result.scalar()
    if null_count > 0:
        raise RuntimeError(
            f"Cannot migrate: {null_count} projects have NULL customer_id. "
            "Assign customer_id to all projects before running this migration."
        )

    # ── Step 1: Add customer_id columns (nullable) ──
    tables = ["assets", "ip_subnets", "port_maps", "policy_assignments"]
    for table in tables:
        if not _column_exists(table, "customer_id"):
            op.add_column(
                table,
                sa.Column(
                    "customer_id",
                    sa.Integer(),
                    sa.ForeignKey("customers.id"),
                    nullable=True,
                ),
            )
        if not _index_exists(table, f"ix_{table}_customer_id"):
            op.create_index(f"ix_{table}_customer_id", table, ["customer_id"])

    # ── Step 2: Project.customer_id NOT NULL ──
    op.alter_column("projects", "customer_id", nullable=False)

    # ── Step 3: Backfill customer_id from project ──
    for table in tables:
        conn.execute(
            sa.text(
                f"UPDATE {table} t "
                "SET customer_id = p.customer_id "
                "FROM projects p "
                "WHERE t.project_id = p.id "
                "AND t.customer_id IS NULL"
            )
        )

    # ── Step 4: Make customer_id NOT NULL ──
    for table in tables:
        op.alter_column(table, "customer_id", nullable=False)

    # ── Step 5: Drop project_id FK and column ──
    for table in tables:
        fk_name = f"{table}_project_id_fkey"
        if _fk_exists(table, fk_name):
            op.drop_constraint(fk_name, table, type_="foreignkey")

        idx_name = f"ix_{table}_project_id"
        if _index_exists(table, idx_name):
            op.drop_index(idx_name, table_name=table)

        if _column_exists(table, "project_id"):
            op.drop_column(table, "project_id")


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not supported for customer-centric restructure. "
        "Restore from DB backup if rollback is needed."
    )

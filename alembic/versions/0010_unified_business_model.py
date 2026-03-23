"""Unified business model: merge projects into contract_periods, rename tables.

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-23
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def _constraint_name(table: str, column: str, kind: str = "fkey") -> str | None:
    """Look up an actual constraint name from the DB inspector."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if kind == "fkey":
        for fk in inspector.get_foreign_keys(table):
            if column in fk["constrained_columns"]:
                return fk["name"]
    return None


def _unique_constraint_name(table: str, columns: list[str]) -> str | None:
    """Look up a unique constraint by its column set."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    col_set = set(columns)
    for uc in inspector.get_unique_constraints(table):
        if set(uc["column_names"]) == col_set:
            return uc["name"]
    return None


def upgrade() -> None:
    conn = op.get_bind()

    # ================================================================
    # Step 1: Create contract_sales_details table
    # ================================================================
    op.create_table(
        "contract_sales_details",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "contract_period_id",
            sa.Integer(),
            sa.ForeignKey("contract_periods.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("expected_revenue_amount", sa.Integer(), server_default=sa.text("0")),
        sa.Column("expected_gp_amount", sa.Integer(), server_default=sa.text("0")),
        sa.Column("inspection_day", sa.Integer(), nullable=True),
        sa.Column("inspection_date", sa.Date(), nullable=True),
        sa.Column("invoice_month_offset", sa.Integer(), nullable=True),
        sa.Column("invoice_day_type", sa.String(20), nullable=True),
        sa.Column("invoice_day", sa.Integer(), nullable=True),
        sa.Column("invoice_holiday_adjust", sa.String(10), nullable=True),
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
            nullable=False,
        ),
    )

    # ================================================================
    # Step 2: Add description column to contract_periods
    # ================================================================
    if not _column_exists("contract_periods", "description"):
        op.add_column(
            "contract_periods",
            sa.Column("description", sa.Text(), nullable=True),
        )

    # ================================================================
    # Step 3: Copy sales fields from contract_periods to contract_sales_details
    # ================================================================
    conn.execute(
        sa.text(
            """
            INSERT INTO contract_sales_details
                (contract_period_id, expected_revenue_amount, expected_gp_amount,
                 inspection_day, inspection_date, invoice_month_offset,
                 invoice_day_type, invoice_day, invoice_holiday_adjust)
            SELECT id, expected_revenue_total, expected_gp_total,
                   inspection_day, inspection_date, invoice_month_offset,
                   invoice_day_type, invoice_day, invoice_holiday_adjust
            FROM contract_periods
            """
        )
    )

    # ================================================================
    # Step 4: Drop sales columns from contract_periods
    # ================================================================
    cp_drop_cols = [
        "expected_revenue_total",
        "expected_gp_total",
        "inspection_day",
        "inspection_date",
        "invoice_month_offset",
        "invoice_day_type",
        "invoice_day",
        "invoice_holiday_adjust",
    ]
    for col in cp_drop_cols:
        if _column_exists("contract_periods", col):
            op.drop_column("contract_periods", col)

    # ================================================================
    # Step 5: Drop inspection/invoice columns from contracts
    # ================================================================
    contracts_drop_cols = [
        "inspection_day",
        "inspection_date",
        "invoice_month_offset",
        "invoice_day_type",
        "invoice_day",
        "invoice_holiday_adjust",
    ]
    for col in contracts_drop_cols:
        if _column_exists("contracts", col):
            op.drop_column("contracts", col)

    # ================================================================
    # Step 6: Map project_id → contract_period_id for infra tables
    # ================================================================

    # 6a: Create temp mapping table
    conn.execute(
        sa.text(
            """
            CREATE TEMP TABLE _project_period_map AS
            SELECT DISTINCT ON (p.id)
                p.id AS project_id,
                COALESCE(
                    (SELECT cp.id FROM contract_periods cp
                     WHERE cp.contract_id = pcl.contract_id
                     ORDER BY cp.period_year DESC LIMIT 1),
                    NULL
                ) AS contract_period_id
            FROM projects p
            LEFT JOIN project_contract_links pcl ON pcl.project_id = p.id
            ORDER BY p.id, pcl.is_primary DESC NULLS LAST, pcl.id ASC
            """
        )
    )

    # 6b: Handle orphan projects (no contract mapping)
    orphans = conn.execute(
        sa.text(
            """
            SELECT m.project_id, p.project_code, p.project_name,
                   p.customer_id, p.start_date, p.description
            FROM _project_period_map m
            JOIN projects p ON p.id = m.project_id
            WHERE m.contract_period_id IS NULL
            """
        )
    ).fetchall()

    for orphan in orphans:
        project_id = orphan[0]
        project_code = orphan[1]
        project_name = orphan[2]
        customer_id = orphan[3]
        start_date = orphan[4]
        description = orphan[5]

        # Derive year from start_date or default 2026
        if start_date is not None:
            period_year = start_date.year
        else:
            period_year = 2026

        # Determine unique contract_code (append -MIG on collision)
        code = project_code
        if code:
            existing = conn.execute(
                sa.text("SELECT 1 FROM contracts WHERE contract_code = :code"),
                {"code": code},
            ).first()
            if existing:
                code = f"{code}-MIG"

        # Create a new contract
        result = conn.execute(
            sa.text(
                """
                INSERT INTO contracts (contract_code, contract_name, contract_type,
                                       end_customer_id, status, created_at, updated_at)
                VALUES (:code, :name, 'ETC', :customer_id, 'active', now(), now())
                RETURNING id
                """
            ),
            {
                "code": code,
                "name": project_name or "Migrated Project",
                "customer_id": customer_id,
            },
        )
        contract_id = result.scalar_one()

        # Create a new contract_period
        result = conn.execute(
            sa.text(
                """
                INSERT INTO contract_periods (contract_id, period_year, period_label,
                                              stage, description, created_at, updated_at)
                VALUES (:contract_id, :period_year, :period_label,
                        '50%%', :description, now(), now())
                RETURNING id
                """
            ),
            {
                "contract_id": contract_id,
                "period_year": period_year,
                "period_label": f"Y{str(period_year)[-2:]}",
                "description": description,
            },
        )
        period_id = result.scalar_one()

        # Also insert a sales_details row for the new period
        conn.execute(
            sa.text(
                """
                INSERT INTO contract_sales_details (contract_period_id, created_at, updated_at)
                VALUES (:period_id, now(), now())
                """
            ),
            {"period_id": period_id},
        )

        # Update the mapping
        conn.execute(
            sa.text(
                """
                UPDATE _project_period_map
                SET contract_period_id = :period_id
                WHERE project_id = :project_id
                """
            ),
            {"period_id": period_id, "project_id": project_id},
        )

    # 6c: Add contract_period_id to infra tables, map data, drop project_id
    infra_tables = ["project_phases", "project_assets", "project_customers"]

    for table in infra_tables:
        # Add nullable contract_period_id column
        if not _column_exists(table, "contract_period_id"):
            op.add_column(
                table,
                sa.Column("contract_period_id", sa.Integer(), nullable=True),
            )

        # Populate from mapping table
        conn.execute(
            sa.text(
                f"""
                UPDATE {table} t
                SET contract_period_id = m.contract_period_id
                FROM _project_period_map m
                WHERE t.project_id = m.project_id
                """
            )
        )

        # Delete rows that still have NULL contract_period_id
        # (orphan rows with no project in mapping — shouldn't happen, but safety)
        conn.execute(
            sa.text(
                f"DELETE FROM {table} WHERE contract_period_id IS NULL"
            )
        )

        # Make NOT NULL
        op.alter_column(table, "contract_period_id", nullable=False)

        # Drop old FK on project_id
        fk_name = _constraint_name(table, "project_id", "fkey")
        if fk_name:
            op.drop_constraint(fk_name, table, type_="foreignkey")

        # Drop project_id column
        if _column_exists(table, "project_id"):
            op.drop_column(table, "project_id")

        # Add new FK to contract_periods
        op.create_foreign_key(
            f"{table}_contract_period_id_fkey",
            table,
            "contract_periods",
            ["contract_period_id"],
            ["id"],
        )

    # 6d: Update unique constraints
    # project_assets(project_id, asset_id) → (contract_period_id, asset_id)
    old_uc = _unique_constraint_name("project_assets", ["contract_period_id", "asset_id"])
    if old_uc is None:
        # The old constraint on (project_id, asset_id) was already dropped with the column.
        # Create the new one.
        op.create_unique_constraint(
            "uq_period_asset",
            "project_assets",
            ["contract_period_id", "asset_id"],
        )

    # project_customers(project_id, customer_id, role) → (contract_period_id, customer_id, role)
    old_uc2 = _unique_constraint_name("project_customers", ["contract_period_id", "customer_id", "role"])
    if old_uc2 is None:
        op.create_unique_constraint(
            "uq_period_customer_role",
            "project_customers",
            ["contract_period_id", "customer_id", "role"],
        )

    # ================================================================
    # Step 7: Rename tables
    # ================================================================
    op.rename_table("project_phases", "period_phases")
    op.rename_table("project_deliverables", "period_deliverables")
    op.rename_table("project_assets", "period_assets")
    op.rename_table("project_customers", "period_customers")
    op.rename_table("project_customer_contacts", "period_customer_contacts")

    # Rename column: period_deliverables.project_phase_id → period_phase_id
    op.alter_column("period_deliverables", "project_phase_id", new_column_name="period_phase_id")

    # Update FK for period_deliverables.period_phase_id
    old_fk = _constraint_name("period_deliverables", "period_phase_id", "fkey")
    if old_fk:
        op.drop_constraint(old_fk, "period_deliverables", type_="foreignkey")
    op.create_foreign_key(
        "period_deliverables_period_phase_id_fkey",
        "period_deliverables",
        "period_phases",
        ["period_phase_id"],
        ["id"],
    )

    # Rename column: period_customer_contacts.project_customer_id → period_customer_id
    op.alter_column("period_customer_contacts", "project_customer_id", new_column_name="period_customer_id")

    # Update FK for period_customer_contacts.period_customer_id
    old_fk2 = _constraint_name("period_customer_contacts", "period_customer_id", "fkey")
    if old_fk2:
        op.drop_constraint(old_fk2, "period_customer_contacts", type_="foreignkey")
    op.create_foreign_key(
        "period_customer_contacts_period_customer_id_fkey",
        "period_customer_contacts",
        "period_customers",
        ["period_customer_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ================================================================
    # Step 8: Drop old tables
    # ================================================================
    op.drop_table("project_contract_links")
    op.drop_table("projects")

    # ================================================================
    # Step 9: Update audit logs
    # ================================================================
    conn.execute(
        sa.text(
            "UPDATE audit_logs SET entity_type = 'contract_period' "
            "WHERE entity_type = 'project'"
        )
    )


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")

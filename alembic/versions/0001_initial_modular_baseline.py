"""Initial modular baseline: all tables for common, accounting, infra modules.

Revision ID: 0001
Revises:
Create Date: 2026-03-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    """Check if table already exists (idempotent)."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ================================================================
    # COMMON MODULE
    # ================================================================

    # -- roles --
    if not _table_exists("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
            sa.Column("name", sa.String(100), unique=True, nullable=False),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("permissions", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- users --
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("login_id", sa.String(100), unique=True, nullable=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("department", sa.String(100), nullable=True),
            sa.Column("position", sa.String(100), nullable=True),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("password_hash", sa.String(255), nullable=True),
            sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- login_failures --
    if not _table_exists("login_failures"):
        op.create_table(
            "login_failures",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("login_id", sa.String(100), unique=True, nullable=False, index=True),
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("locked_until", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- user_preferences --
    if not _table_exists("user_preferences"):
        op.create_table(
            "user_preferences",
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("key", sa.String(100), primary_key=True),
            sa.Column("value", sa.String(500), nullable=True),
        )

    # -- customers --
    if not _table_exists("customers"):
        op.create_table(
            "customers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("business_no", sa.String(50), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("customer_type", sa.String(50), nullable=True),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column("address", sa.String(500), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- customer_contacts --
    if not _table_exists("customer_contacts"):
        op.create_table(
            "customer_contacts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column("email", sa.String(200), nullable=True),
            sa.Column("contact_type", sa.String(20), nullable=False, server_default=sa.text("''")),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("department", sa.String(100), nullable=True),
            sa.Column("title", sa.String(100), nullable=True),
            sa.Column("emergency_phone", sa.String(50), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- customer_contact_roles --
    if not _table_exists("customer_contact_roles"):
        op.create_table(
            "customer_contact_roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "customer_contact_id",
                sa.Integer(),
                sa.ForeignKey("customer_contacts.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("role_type", sa.String(20), nullable=False),
            sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("customer_contact_id", "role_type", name="uq_contact_role"),
        )

    # -- settings --
    if not _table_exists("settings"):
        op.create_table(
            "settings",
            sa.Column("key", sa.String(100), primary_key=True),
            sa.Column("value", sa.String(500), nullable=True),
        )

    # -- term_configs --
    if not _table_exists("term_configs"):
        op.create_table(
            "term_configs",
            sa.Column("term_key", sa.String(50), primary_key=True),
            sa.Column("category", sa.String(30), nullable=False),
            sa.Column("standard_label_en", sa.String(100), nullable=False),
            sa.Column("standard_label_ko", sa.String(100), nullable=False),
            sa.Column("definition", sa.Text(), nullable=True),
            sa.Column("default_ui_label", sa.String(50), nullable=False),
            sa.Column("custom_ui_label", sa.String(50), nullable=True),
            sa.Column("is_customized", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        )

    # -- audit_logs --
    if not _table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("entity_type", sa.String(50), nullable=False, index=True),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("summary", sa.String(500), nullable=True),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), index=True),
        )

    # ================================================================
    # ACCOUNTING MODULE
    # ================================================================

    # -- contracts --
    if not _table_exists("contracts"):
        op.create_table(
            "contracts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("contract_code", sa.String(50), unique=True, nullable=True),
            sa.Column("contract_name", sa.String(300), nullable=False),
            sa.Column("contract_type", sa.String(30), nullable=False, index=True),
            sa.Column("end_customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
            sa.Column(
                "owner_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("status", sa.String(30), server_default=sa.text("'active'"), index=True),
            sa.Column("notes", sa.String(500), nullable=True),
            sa.Column("inspection_day", sa.Integer(), nullable=True),
            sa.Column("inspection_date", sa.Date(), nullable=True),
            sa.Column("invoice_month_offset", sa.Integer(), nullable=True),
            sa.Column("invoice_day_type", sa.String(20), nullable=True),
            sa.Column("invoice_day", sa.Integer(), nullable=True),
            sa.Column("invoice_holiday_adjust", sa.String(10), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- contract_periods --
    if not _table_exists("contract_periods"):
        op.create_table(
            "contract_periods",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False, index=True),
            sa.Column("period_year", sa.Integer(), nullable=False),
            sa.Column("period_label", sa.String(20), nullable=False),
            sa.Column("stage", sa.String(50), nullable=False),
            sa.Column("expected_revenue_total", sa.Integer(), server_default=sa.text("0")),
            sa.Column("expected_gp_total", sa.Integer(), server_default=sa.text("0")),
            sa.Column("start_month", sa.String(10), nullable=True, index=True),
            sa.Column("end_month", sa.String(10), nullable=True, index=True),
            sa.Column(
                "owner_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "customer_id",
                sa.Integer(),
                sa.ForeignKey("customers.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("is_completed", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("is_planned", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("notes", sa.String(500), nullable=True),
            sa.Column("inspection_day", sa.Integer(), nullable=True),
            sa.Column("inspection_date", sa.Date(), nullable=True),
            sa.Column("invoice_month_offset", sa.Integer(), nullable=True),
            sa.Column("invoice_day_type", sa.String(20), nullable=True),
            sa.Column("invoice_day", sa.Integer(), nullable=True),
            sa.Column("invoice_holiday_adjust", sa.String(10), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("contract_id", "period_year", name="uq_contract_period"),
        )

    # -- contract_contacts --
    if not _table_exists("contract_contacts"):
        op.create_table(
            "contract_contacts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "contract_period_id",
                sa.Integer(),
                sa.ForeignKey("contract_periods.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False, index=True),
            sa.Column(
                "customer_contact_id",
                sa.Integer(),
                sa.ForeignKey("customer_contacts.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("contact_type", sa.String(20), nullable=False),
            sa.Column("rank", sa.String(10), nullable=False, server_default=sa.text("'정'")),
            sa.Column("notes", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- contract_type_configs --
    if not _table_exists("contract_type_configs"):
        op.create_table(
            "contract_type_configs",
            sa.Column("code", sa.String(30), primary_key=True),
            sa.Column("label", sa.String(50), nullable=False),
            sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("default_gp_pct", sa.Integer(), nullable=True),
            sa.Column("default_inspection_day", sa.Integer(), nullable=True),
            sa.Column("default_invoice_month_offset", sa.Integer(), nullable=True),
            sa.Column("default_invoice_day_type", sa.String(20), nullable=True),
            sa.Column("default_invoice_day", sa.Integer(), nullable=True),
            sa.Column("default_invoice_holiday_adjust", sa.String(10), nullable=True),
        )

    # -- monthly_forecasts --
    if not _table_exists("monthly_forecasts"):
        op.create_table(
            "monthly_forecasts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "contract_period_id",
                sa.Integer(),
                sa.ForeignKey("contract_periods.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("forecast_month", sa.String(10), nullable=False, index=True),
            sa.Column("revenue_amount", sa.Integer(), server_default=sa.text("0")),
            sa.Column("gp_amount", sa.Integer(), server_default=sa.text("0")),
            sa.Column("version_no", sa.Integer(), server_default=sa.text("1")),
            sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), index=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "contract_period_id", "forecast_month", "version_no", name="uq_forecast"
            ),
        )

    # -- transaction_lines --
    if not _table_exists("transaction_lines"):
        op.create_table(
            "transaction_lines",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False, index=True),
            sa.Column("revenue_month", sa.String(10), nullable=False, index=True),
            sa.Column("line_type", sa.String(20), nullable=False),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
            sa.Column("supply_amount", sa.Integer(), nullable=False),
            sa.Column("invoice_issue_date", sa.String(10), nullable=True),
            sa.Column("status", sa.String(20), server_default=sa.text("'확정'")),
            sa.Column("description", sa.String(300), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- receipts --
    if not _table_exists("receipts"):
        op.create_table(
            "receipts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("contract_id", sa.Integer(), sa.ForeignKey("contracts.id"), nullable=False, index=True),
            sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True),
            sa.Column("receipt_date", sa.String(10), nullable=False, index=True),
            sa.Column("revenue_month", sa.String(10), nullable=True, index=True),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("description", sa.String(300), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- receipt_matches --
    if not _table_exists("receipt_matches"):
        op.create_table(
            "receipt_matches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "receipt_id",
                sa.Integer(),
                sa.ForeignKey("receipts.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "transaction_line_id",
                sa.Integer(),
                sa.ForeignKey("transaction_lines.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("matched_amount", sa.Integer(), nullable=False),
            sa.Column("match_type", sa.String(20), nullable=False, server_default=sa.text("'auto'")),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "receipt_id", "transaction_line_id", name="uq_receipt_match_receipt_transaction_line"
            ),
        )

    # ================================================================
    # INFRA MODULE
    # ================================================================

    # -- projects --
    if not _table_exists("projects"):
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_code", sa.String(50), unique=True, index=True),
            sa.Column("project_name", sa.String(255), index=True),
            sa.Column(
                "customer_id",
                sa.Integer(),
                sa.ForeignKey("customers.id"),
                nullable=True,
            ),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(30), server_default=sa.text("'planned'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- project_phases --
    if not _table_exists("project_phases"):
        op.create_table(
            "project_phases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), index=True),
            sa.Column("phase_type", sa.String(30)),
            sa.Column("task_scope", sa.Text(), nullable=True),
            sa.Column("deliverables_note", sa.Text(), nullable=True),
            sa.Column("cautions", sa.Text(), nullable=True),
            sa.Column("submission_required", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("submission_status", sa.String(30), server_default=sa.text("'pending'")),
            sa.Column("status", sa.String(30), server_default=sa.text("'not_started'")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- project_deliverables --
    if not _table_exists("project_deliverables"):
        op.create_table(
            "project_deliverables",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "project_phase_id",
                sa.Integer(),
                sa.ForeignKey("project_phases.id"),
                index=True,
            ),
            sa.Column("name", sa.String(255)),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_submitted", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("submitted_at", sa.Date(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- assets --
    if not _table_exists("assets"):
        op.create_table(
            "assets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), index=True),
            sa.Column("asset_name", sa.String(255), index=True),
            sa.Column("asset_type", sa.String(50)),
            sa.Column("vendor", sa.String(100), nullable=True),
            sa.Column("model", sa.String(100), nullable=True),
            sa.Column("role", sa.String(100), nullable=True),
            sa.Column("environment", sa.String(30), server_default=sa.text("'prod'")),
            sa.Column("location", sa.String(100), nullable=True),
            sa.Column("status", sa.String(30), server_default=sa.text("'planned'")),
            sa.Column("note", sa.Text(), nullable=True),
            # Equipment Spec
            sa.Column("center", sa.String(100), nullable=True),
            sa.Column("operation_type", sa.String(30), nullable=True),
            sa.Column("equipment_id", sa.String(100), nullable=True),
            sa.Column("rack_no", sa.String(50), nullable=True),
            sa.Column("rack_unit", sa.String(50), nullable=True),
            sa.Column("phase", sa.String(50), nullable=True),
            sa.Column("received_date", sa.Date(), nullable=True),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("subcategory", sa.String(100), nullable=True),
            sa.Column("serial_no", sa.String(200), nullable=True),
            # Logical Config
            sa.Column("hostname", sa.String(255), nullable=True),
            sa.Column("cluster", sa.String(200), nullable=True),
            sa.Column("service_name", sa.String(200), nullable=True),
            sa.Column("zone", sa.String(100), nullable=True),
            sa.Column("service_ip", sa.String(64), nullable=True),
            sa.Column("mgmt_ip", sa.String(64), nullable=True),
            # Hardware Config
            sa.Column("size_unit", sa.Integer(), nullable=True),
            sa.Column("lc_count", sa.Integer(), nullable=True),
            sa.Column("ha_count", sa.Integer(), nullable=True),
            sa.Column("utp_count", sa.Integer(), nullable=True),
            sa.Column("power_count", sa.Integer(), nullable=True),
            sa.Column("power_type", sa.String(50), nullable=True),
            sa.Column("firmware_version", sa.String(100), nullable=True),
            # Asset Info
            sa.Column("asset_class", sa.String(50), nullable=True),
            sa.Column("asset_number", sa.String(100), nullable=True),
            sa.Column("year_acquired", sa.Integer(), nullable=True),
            sa.Column("dept", sa.String(100), nullable=True),
            sa.Column("primary_contact_name", sa.String(100), nullable=True),
            sa.Column("secondary_contact_name", sa.String(100), nullable=True),
            sa.Column("maintenance_vendor", sa.String(200), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- ip_subnets --
    if not _table_exists("ip_subnets"):
        op.create_table(
            "ip_subnets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), index=True),
            sa.Column("name", sa.String(200)),
            sa.Column("subnet", sa.String(64)),
            sa.Column("role", sa.String(30), server_default=sa.text("'service'")),
            sa.Column("vlan_id", sa.String(30), nullable=True),
            sa.Column("gateway", sa.String(64), nullable=True),
            sa.Column("region", sa.String(100), nullable=True),
            sa.Column("floor", sa.String(50), nullable=True),
            sa.Column("counterpart", sa.String(200), nullable=True),
            sa.Column("allocation_type", sa.String(50), nullable=True),
            sa.Column("category", sa.String(50), nullable=True),
            sa.Column("netmask", sa.String(64), nullable=True),
            sa.Column("zone", sa.String(100), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- asset_ips --
    if not _table_exists("asset_ips"):
        op.create_table(
            "asset_ips",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), index=True),
            sa.Column(
                "ip_subnet_id",
                sa.Integer(),
                sa.ForeignKey("ip_subnets.id"),
                nullable=True,
                index=True,
            ),
            sa.Column("ip_address", sa.String(64), index=True),
            sa.Column("ip_type", sa.String(30), server_default=sa.text("'service'")),
            sa.Column("interface_name", sa.String(100), nullable=True),
            sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("zone", sa.String(100), nullable=True),
            sa.Column("service_name", sa.String(200), nullable=True),
            sa.Column("hostname", sa.String(255), nullable=True),
            sa.Column("vlan_id", sa.String(30), nullable=True),
            sa.Column("network", sa.String(64), nullable=True),
            sa.Column("netmask", sa.String(64), nullable=True),
            sa.Column("gateway", sa.String(64), nullable=True),
            sa.Column("dns_primary", sa.String(64), nullable=True),
            sa.Column("dns_secondary", sa.String(64), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- port_maps --
    if not _table_exists("port_maps"):
        op.create_table(
            "port_maps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), index=True),
            sa.Column("src_asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
            sa.Column("src_ip", sa.String(64), nullable=True),
            sa.Column("dst_asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
            sa.Column("dst_ip", sa.String(64), nullable=True),
            sa.Column("protocol", sa.String(20), nullable=True),
            sa.Column("port", sa.Integer(), nullable=True),
            sa.Column("purpose", sa.String(255), nullable=True),
            sa.Column("status", sa.String(30), server_default=sa.text("'required'")),
            sa.Column("note", sa.Text(), nullable=True),
            # Common
            sa.Column("seq", sa.Integer(), nullable=True),
            sa.Column("cable_no", sa.String(100), nullable=True),
            sa.Column("cable_request", sa.String(200), nullable=True),
            sa.Column("connection_type", sa.String(50), nullable=True),
            sa.Column("summary", sa.String(500), nullable=True),
            # Start side
            sa.Column("src_mid", sa.String(100), nullable=True),
            sa.Column("src_rack_no", sa.String(50), nullable=True),
            sa.Column("src_rack_unit", sa.String(50), nullable=True),
            sa.Column("src_vendor", sa.String(100), nullable=True),
            sa.Column("src_model", sa.String(100), nullable=True),
            sa.Column("src_hostname", sa.String(255), nullable=True),
            sa.Column("src_cluster", sa.String(200), nullable=True),
            sa.Column("src_slot", sa.String(30), nullable=True),
            sa.Column("src_port_name", sa.String(30), nullable=True),
            sa.Column("src_service_name", sa.String(200), nullable=True),
            sa.Column("src_zone", sa.String(100), nullable=True),
            sa.Column("src_vlan", sa.String(30), nullable=True),
            # End side
            sa.Column("dst_mid", sa.String(100), nullable=True),
            sa.Column("dst_rack_no", sa.String(50), nullable=True),
            sa.Column("dst_rack_unit", sa.String(50), nullable=True),
            sa.Column("dst_vendor", sa.String(100), nullable=True),
            sa.Column("dst_model", sa.String(100), nullable=True),
            sa.Column("dst_hostname", sa.String(255), nullable=True),
            sa.Column("dst_cluster", sa.String(200), nullable=True),
            sa.Column("dst_slot", sa.String(30), nullable=True),
            sa.Column("dst_port_name", sa.String(30), nullable=True),
            sa.Column("dst_service_name", sa.String(200), nullable=True),
            sa.Column("dst_zone", sa.String(100), nullable=True),
            sa.Column("dst_vlan", sa.String(30), nullable=True),
            # Cable info
            sa.Column("cable_type", sa.String(30), nullable=True),
            sa.Column("cable_speed", sa.String(30), nullable=True),
            sa.Column("duplex", sa.String(30), nullable=True),
            sa.Column("cable_category", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- policy_definitions --
    if not _table_exists("policy_definitions"):
        op.create_table(
            "policy_definitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("policy_code", sa.String(50), unique=True, index=True),
            sa.Column("policy_name", sa.String(255)),
            sa.Column("category", sa.String(100)),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("security_domain", sa.String(200), nullable=True),
            sa.Column("requirement", sa.Text(), nullable=True),
            sa.Column("architecture_element", sa.String(200), nullable=True),
            sa.Column("control_point", sa.String(200), nullable=True),
            sa.Column("iso27001_ref", sa.String(100), nullable=True),
            sa.Column("nist_ref", sa.String(100), nullable=True),
            sa.Column("isms_p_ref", sa.String(100), nullable=True),
            sa.Column("implementation_example", sa.Text(), nullable=True),
            sa.Column("evidence", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- policy_assignments --
    if not _table_exists("policy_assignments"):
        op.create_table(
            "policy_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), index=True),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
            sa.Column(
                "policy_definition_id",
                sa.Integer(),
                sa.ForeignKey("policy_definitions.id"),
                index=True,
            ),
            sa.Column("status", sa.String(30), server_default=sa.text("'not_checked'")),
            sa.Column("exception_reason", sa.Text(), nullable=True),
            sa.Column("checked_by", sa.String(100), nullable=True),
            sa.Column("checked_date", sa.Date(), nullable=True),
            sa.Column("evidence_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    # -- asset_contacts --
    if not _table_exists("asset_contacts"):
        op.create_table(
            "asset_contacts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), index=True),
            sa.Column(
                "contact_id",
                sa.Integer(),
                sa.ForeignKey("customer_contacts.id"),
                index=True,
            ),
            sa.Column("role", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    # Drop in reverse dependency order
    # Infra
    op.drop_table("asset_contacts")
    op.drop_table("policy_assignments")
    op.drop_table("policy_definitions")
    op.drop_table("port_maps")
    op.drop_table("asset_ips")
    op.drop_table("ip_subnets")
    op.drop_table("assets")
    op.drop_table("project_deliverables")
    op.drop_table("project_phases")
    op.drop_table("projects")
    # Accounting
    op.drop_table("receipt_matches")
    op.drop_table("receipts")
    op.drop_table("transaction_lines")
    op.drop_table("monthly_forecasts")
    op.drop_table("contract_type_configs")
    op.drop_table("contract_contacts")
    op.drop_table("contract_periods")
    op.drop_table("contracts")
    # Common
    op.drop_table("audit_logs")
    op.drop_table("term_configs")
    op.drop_table("settings")
    op.drop_table("customer_contact_roles")
    op.drop_table("customer_contacts")
    op.drop_table("customers")
    op.drop_table("user_preferences")
    op.drop_table("login_failures")
    op.drop_table("users")
    op.drop_table("roles")

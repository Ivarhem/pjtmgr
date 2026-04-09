# inframgr Alembic Migrations Reference

# ============================================
# FILE: alembic/versions/20260317_1300_initial_inventory_schema.py
# ============================================
"""initial inventory schema

Revision ID: 20260317_1300
Revises:
Create Date: 2026-03-17 13:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260317_1300"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _create_index(table_name: str, index_name: str, columns: list[str], unique: bool = False) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    if not _table_exists("projects"):
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_code", sa.String(length=50), nullable=False),
            sa.Column("project_name", sa.String(length=255), nullable=False),
            sa.Column("client_name", sa.String(length=255), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="planned"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("projects", "ix_projects_project_code", ["project_code"], unique=True)
    _create_index("projects", "ix_projects_project_name", ["project_name"])

    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("login_id", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("users", "ix_users_login_id", ["login_id"], unique=True)

    if not _table_exists("policy_definitions"):
        op.create_table(
            "policy_definitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("policy_code", sa.String(length=50), nullable=False),
            sa.Column("policy_name", sa.String(length=255), nullable=False),
            sa.Column("category", sa.String(length=100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("policy_definitions", "ix_policy_definitions_policy_code", ["policy_code"], unique=True)

    if not _table_exists("project_phases"):
        op.create_table(
            "project_phases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("phase_type", sa.String(length=30), nullable=False),
            sa.Column("task_scope", sa.Text(), nullable=True),
            sa.Column("deliverables_note", sa.Text(), nullable=True),
            sa.Column("cautions", sa.Text(), nullable=True),
            sa.Column("submission_required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("submission_status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="not_started"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("project_phases", "ix_project_phases_project_id", ["project_id"])

    if not _table_exists("assets"):
        op.create_table(
            "assets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("asset_name", sa.String(length=255), nullable=False),
            sa.Column("asset_type", sa.String(length=50), nullable=False),
            sa.Column("vendor", sa.String(length=100), nullable=True),
            sa.Column("model", sa.String(length=100), nullable=True),
            sa.Column("role", sa.String(length=100), nullable=True),
            sa.Column("environment", sa.String(length=30), nullable=False, server_default="prod"),
            sa.Column("location", sa.String(length=100), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="planned"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("assets", "ix_assets_project_id", ["project_id"])
    _create_index("assets", "ix_assets_asset_name", ["asset_name"])

    if not _table_exists("partners"):
        op.create_table(
            "partners",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("partner_name", sa.String(length=255), nullable=False),
            sa.Column("partner_type", sa.String(length=50), nullable=False),
            sa.Column("contact_phone", sa.String(length=50), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("partners", "ix_partners_partner_name", ["partner_name"])

    if not _table_exists("project_deliverables"):
        op.create_table(
            "project_deliverables",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_phase_id", sa.Integer(), sa.ForeignKey("project_phases.id"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_submitted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("submitted_at", sa.Date(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("project_deliverables", "ix_project_deliverables_project_phase_id", ["project_phase_id"])

    if not _table_exists("asset_ips"):
        op.create_table(
            "asset_ips",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
            sa.Column("ip_address", sa.String(length=64), nullable=False),
            sa.Column("subnet", sa.String(length=64), nullable=True),
            sa.Column("ip_type", sa.String(length=30), nullable=False, server_default="service"),
            sa.Column("interface_name", sa.String(length=100), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("asset_ips", "ix_asset_ips_asset_id", ["asset_id"])
    _create_index("asset_ips", "ix_asset_ips_ip_address", ["ip_address"])

    if not _table_exists("contacts"):
        op.create_table(
            "contacts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id"), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("role", sa.String(length=100), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("emergency_phone", sa.String(length=50), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("contacts", "ix_contacts_partner_id", ["partner_id"])

    if not _table_exists("port_maps"):
        op.create_table(
            "port_maps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("src_asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
            sa.Column("src_ip", sa.String(length=64), nullable=True),
            sa.Column("dst_asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
            sa.Column("dst_ip", sa.String(length=64), nullable=True),
            sa.Column("protocol", sa.String(length=20), nullable=False, server_default="tcp"),
            sa.Column("port", sa.Integer(), nullable=False),
            sa.Column("purpose", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="required"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("port_maps", "ix_port_maps_project_id", ["project_id"])

    if not _table_exists("policy_assignments"):
        op.create_table(
            "policy_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=True),
            sa.Column("policy_definition_id", sa.Integer(), sa.ForeignKey("policy_definitions.id"), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="not_checked"),
            sa.Column("exception_reason", sa.Text(), nullable=True),
            sa.Column("checked_by", sa.String(length=100), nullable=True),
            sa.Column("checked_date", sa.Date(), nullable=True),
            sa.Column("evidence_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("policy_assignments", "ix_policy_assignments_project_id", ["project_id"])
    _create_index("policy_assignments", "ix_policy_assignments_policy_definition_id", ["policy_definition_id"])

    if not _table_exists("asset_contacts"):
        op.create_table(
            "asset_contacts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
            sa.Column("contact_id", sa.Integer(), sa.ForeignKey("contacts.id"), nullable=False),
            sa.Column("role", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    _create_index("asset_contacts", "ix_asset_contacts_asset_id", ["asset_id"])
    _create_index("asset_contacts", "ix_asset_contacts_contact_id", ["contact_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in [
        "asset_contacts",
        "policy_assignments",
        "port_maps",
        "contacts",
        "asset_ips",
        "project_deliverables",
        "partners",
        "assets",
        "project_phases",
        "policy_definitions",
        "users",
        "projects",
    ]:
        if sa.inspect(bind).has_table(table_name):
            op.drop_table(table_name)


# ============================================
# FILE: alembic/versions/20260317_1400_add_ip_subnets_table.py
# ============================================
"""add ip_subnets table and update asset_ips

Revision ID: 20260317_1400
Revises: 20260317_1300
Create Date: 2026-03-17 14:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260317_1400"
down_revision: str = "20260317_1300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    columns = [c["name"] for c in _inspector().get_columns(table_name)]
    return column_name in columns


def _index_exists(table_name: str, index_name: str) -> bool:
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def upgrade() -> None:
    # 1. ip_subnets 테이블 생성
    if not _table_exists("ip_subnets"):
        op.create_table(
            "ip_subnets",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("subnet", sa.String(length=64), nullable=False),
            sa.Column("role", sa.String(length=30), nullable=False, server_default="service"),
            sa.Column("vlan_id", sa.String(length=30), nullable=True),
            sa.Column("gateway", sa.String(length=64), nullable=True),
            sa.Column("region", sa.String(length=100), nullable=True),
            sa.Column("floor", sa.String(length=50), nullable=True),
            sa.Column("counterpart", sa.String(length=200), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _index_exists("ip_subnets", "ix_ip_subnets_project_id"):
        op.create_index("ix_ip_subnets_project_id", "ip_subnets", ["project_id"])

    # 2. asset_ips: ip_subnet_id FK 추가, subnet 컬럼 제거
    if not _column_exists("asset_ips", "ip_subnet_id"):
        op.add_column(
            "asset_ips",
            sa.Column("ip_subnet_id", sa.Integer(), sa.ForeignKey("ip_subnets.id"), nullable=True),
        )
    if not _index_exists("asset_ips", "ix_asset_ips_ip_subnet_id"):
        op.create_index("ix_asset_ips_ip_subnet_id", "asset_ips", ["ip_subnet_id"])

    if _column_exists("asset_ips", "subnet"):
        op.drop_column("asset_ips", "subnet")


def downgrade() -> None:
    # asset_ips: subnet 컬럼 복원, ip_subnet_id 제거
    if not _column_exists("asset_ips", "subnet"):
        op.add_column(
            "asset_ips",
            sa.Column("subnet", sa.String(length=64), nullable=True),
        )

    if _index_exists("asset_ips", "ix_asset_ips_ip_subnet_id"):
        op.drop_index("ix_asset_ips_ip_subnet_id", table_name="asset_ips")

    if _column_exists("asset_ips", "ip_subnet_id"):
        op.drop_column("asset_ips", "ip_subnet_id")

    if _table_exists("ip_subnets"):
        op.drop_table("ip_subnets")


# ============================================
# FILE: alembic/versions/20260317_1500_add_external_id_columns.py
# ============================================
"""Add external_id and external_source columns for sales integration."""

from alembic import op
import sqlalchemy as sa


revision = "20260317_1500"
down_revision = "20260317_1400"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    tables = ["projects", "partners", "contacts", "users"]
    for table in tables:
        if not _column_exists(table, "external_id"):
            op.add_column(table, sa.Column("external_id", sa.Integer(), nullable=True))
        if not _column_exists(table, "external_source"):
            op.add_column(table, sa.Column("external_source", sa.String(30), nullable=True))


def downgrade() -> None:
    tables = ["projects", "partners", "contacts", "users"]
    for table in tables:
        op.drop_column(table, "external_source")
        op.drop_column(table, "external_id")


# ============================================
# FILE: alembic/versions/20260317_1600_expand_models_for_template.py
# ============================================
"""Expand all models to match template.xlsx column density."""

from alembic import op
import sqlalchemy as sa


revision = "20260317_1600"
down_revision = "20260317_1500"
branch_labels = None
depends_on = None


def _col_exists(table: str, column: str) -> bool:
    from sqlalchemy import inspect as sa_inspect

    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return column in [c["name"] for c in inspector.get_columns(table)]


def _add_col(table: str, column: str, col_type: sa.types.TypeEngine) -> None:
    if not _col_exists(table, column):
        op.add_column(table, sa.Column(column, col_type, nullable=True))


def upgrade() -> None:
    # ── Asset expansion ──
    _add_col("assets", "center", sa.String(100))
    _add_col("assets", "operation_type", sa.String(30))
    _add_col("assets", "equipment_id", sa.String(100))
    _add_col("assets", "rack_no", sa.String(50))
    _add_col("assets", "rack_unit", sa.String(50))
    _add_col("assets", "phase", sa.String(50))
    _add_col("assets", "received_date", sa.Date())
    _add_col("assets", "category", sa.String(100))
    _add_col("assets", "subcategory", sa.String(100))
    _add_col("assets", "serial_no", sa.String(200))
    _add_col("assets", "hostname", sa.String(255))
    _add_col("assets", "cluster", sa.String(200))
    _add_col("assets", "service_name", sa.String(200))
    _add_col("assets", "zone", sa.String(100))
    _add_col("assets", "service_ip", sa.String(64))
    _add_col("assets", "mgmt_ip", sa.String(64))
    _add_col("assets", "size_unit", sa.Integer())
    _add_col("assets", "lc_count", sa.Integer())
    _add_col("assets", "ha_count", sa.Integer())
    _add_col("assets", "utp_count", sa.Integer())
    _add_col("assets", "power_count", sa.Integer())
    _add_col("assets", "power_type", sa.String(50))
    _add_col("assets", "firmware_version", sa.String(100))
    _add_col("assets", "asset_class", sa.String(50))
    _add_col("assets", "asset_number", sa.String(100))
    _add_col("assets", "year_acquired", sa.Integer())
    _add_col("assets", "dept", sa.String(100))
    _add_col("assets", "primary_contact_name", sa.String(100))
    _add_col("assets", "secondary_contact_name", sa.String(100))
    _add_col("assets", "maintenance_vendor", sa.String(200))

    # ── PortMap expansion ──
    # Make existing columns nullable
    if _col_exists("port_maps", "port"):
        op.alter_column("port_maps", "port", existing_type=sa.Integer(), nullable=True)
    if _col_exists("port_maps", "protocol"):
        op.alter_column(
            "port_maps", "protocol",
            existing_type=sa.String(20),
            nullable=True,
            server_default=None,
        )

    _add_col("port_maps", "seq", sa.Integer())
    _add_col("port_maps", "cable_no", sa.String(100))
    _add_col("port_maps", "cable_request", sa.String(200))
    _add_col("port_maps", "connection_type", sa.String(50))
    _add_col("port_maps", "summary", sa.String(500))
    # Start side
    _add_col("port_maps", "src_mid", sa.String(100))
    _add_col("port_maps", "src_rack_no", sa.String(50))
    _add_col("port_maps", "src_rack_unit", sa.String(50))
    _add_col("port_maps", "src_vendor", sa.String(100))
    _add_col("port_maps", "src_model", sa.String(100))
    _add_col("port_maps", "src_hostname", sa.String(255))
    _add_col("port_maps", "src_cluster", sa.String(200))
    _add_col("port_maps", "src_slot", sa.String(30))
    _add_col("port_maps", "src_port_name", sa.String(30))
    _add_col("port_maps", "src_service_name", sa.String(200))
    _add_col("port_maps", "src_zone", sa.String(100))
    _add_col("port_maps", "src_vlan", sa.String(30))
    # End side
    _add_col("port_maps", "dst_mid", sa.String(100))
    _add_col("port_maps", "dst_rack_no", sa.String(50))
    _add_col("port_maps", "dst_rack_unit", sa.String(50))
    _add_col("port_maps", "dst_vendor", sa.String(100))
    _add_col("port_maps", "dst_model", sa.String(100))
    _add_col("port_maps", "dst_hostname", sa.String(255))
    _add_col("port_maps", "dst_cluster", sa.String(200))
    _add_col("port_maps", "dst_slot", sa.String(30))
    _add_col("port_maps", "dst_port_name", sa.String(30))
    _add_col("port_maps", "dst_service_name", sa.String(200))
    _add_col("port_maps", "dst_zone", sa.String(100))
    _add_col("port_maps", "dst_vlan", sa.String(30))
    # Cable info
    _add_col("port_maps", "cable_type", sa.String(30))
    _add_col("port_maps", "cable_speed", sa.String(30))
    _add_col("port_maps", "duplex", sa.String(30))
    _add_col("port_maps", "cable_category", sa.String(50))

    # ── IpSubnet expansion ──
    _add_col("ip_subnets", "allocation_type", sa.String(50))
    _add_col("ip_subnets", "category", sa.String(50))
    _add_col("ip_subnets", "netmask", sa.String(64))
    _add_col("ip_subnets", "zone", sa.String(100))

    # ── AssetIP expansion ──
    _add_col("asset_ips", "zone", sa.String(100))
    _add_col("asset_ips", "service_name", sa.String(200))
    _add_col("asset_ips", "hostname", sa.String(255))
    _add_col("asset_ips", "vlan_id", sa.String(30))
    _add_col("asset_ips", "network", sa.String(64))
    _add_col("asset_ips", "netmask", sa.String(64))
    _add_col("asset_ips", "gateway", sa.String(64))
    _add_col("asset_ips", "dns_primary", sa.String(64))
    _add_col("asset_ips", "dns_secondary", sa.String(64))

    # ── PolicyDefinition expansion ──
    _add_col("policy_definitions", "security_domain", sa.String(200))
    _add_col("policy_definitions", "requirement", sa.Text())
    _add_col("policy_definitions", "architecture_element", sa.String(200))
    _add_col("policy_definitions", "control_point", sa.String(200))
    _add_col("policy_definitions", "iso27001_ref", sa.String(100))
    _add_col("policy_definitions", "nist_ref", sa.String(100))
    _add_col("policy_definitions", "isms_p_ref", sa.String(100))
    _add_col("policy_definitions", "implementation_example", sa.Text())
    _add_col("policy_definitions", "evidence", sa.Text())

    # ── Partner expansion ──
    _add_col("partners", "address", sa.String(500))
    _add_col("partners", "business_no", sa.String(50))

    # ── Contact expansion ──
    _add_col("contacts", "department", sa.String(100))
    _add_col("contacts", "title", sa.String(100))


def downgrade() -> None:
    pass  # Additive-only, downgrade not implemented



"""Customer → Partner rename.

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-24

NON-REVERSIBLE: 테이블/컬럼/코드 prefix 변경. 실행 전 DB 백업 권장.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Step 1: 테이블 이름 변경 ──
    op.rename_table("customers", "partners")
    op.rename_table("customer_contacts", "partner_contacts")
    op.rename_table("customer_contact_roles", "partner_contact_roles")
    op.rename_table("period_customers", "period_partners")
    op.rename_table("period_customer_contacts", "period_partner_contacts")

    # ── Step 2: FK 컬럼 이름 변경 ──

    # partners 테이블
    op.alter_column("partners", "customer_code", new_column_name="partner_code")
    op.alter_column("partners", "customer_type", new_column_name="partner_type")

    # partner_contacts 테이블
    op.alter_column("partner_contacts", "customer_id", new_column_name="partner_id")

    # partner_contact_roles 테이블
    op.alter_column("partner_contact_roles", "customer_contact_id", new_column_name="partner_contact_id")

    # contracts 테이블
    op.alter_column("contracts", "end_customer_id", new_column_name="end_partner_id")

    # contract_periods 테이블
    op.alter_column("contract_periods", "customer_id", new_column_name="partner_id")

    # period_partners 테이블
    op.alter_column("period_partners", "customer_id", new_column_name="partner_id")

    # period_partner_contacts 테이블
    op.alter_column("period_partner_contacts", "period_customer_id", new_column_name="period_partner_id")

    # transaction_lines 테이블 (accounting)
    op.alter_column("transaction_lines", "customer_id", new_column_name="partner_id")

    # receipts 테이블 (accounting)
    op.alter_column("receipts", "customer_id", new_column_name="partner_id")

    # contract_contacts 테이블 (accounting)
    op.alter_column("contract_contacts", "customer_id", new_column_name="partner_id")
    op.alter_column("contract_contacts", "customer_contact_id", new_column_name="partner_contact_id")

    # assets 테이블 (infra)
    op.alter_column("assets", "customer_id", new_column_name="partner_id")

    # ip_subnets 테이블 (infra)
    op.alter_column("ip_subnets", "customer_id", new_column_name="partner_id")

    # policy_assignments 테이블 (infra)
    op.alter_column("policy_assignments", "customer_id", new_column_name="partner_id")

    # port_maps 테이블 (infra)
    op.alter_column("port_maps", "customer_id", new_column_name="partner_id")

    # ── Step 3: 코드 prefix 변환 ──
    conn = op.get_bind()

    # partner_code: C→P
    conn.execute(text(
        "UPDATE partners SET partner_code = 'P' || SUBSTRING(partner_code FROM 2) "
        "WHERE partner_code LIKE 'C%'"
    ))

    # contract_code: C000-P000 → P000-B000 (FROM 7 skips the old '-P' prefix)
    conn.execute(text(
        "UPDATE contracts SET contract_code = "
        "'P' || SUBSTRING(contract_code FROM 2 FOR 3) || '-B' || SUBSTRING(contract_code FROM 7) "
        "WHERE contract_code LIKE 'C%'"
    ))

    # period_code: C000-P000-Y26A → P000-B000-Y26A
    conn.execute(text(
        "UPDATE contract_periods SET period_code = "
        "'P' || SUBSTRING(period_code FROM 2 FOR 3) || '-B' || SUBSTRING(period_code FROM 7) "
        "WHERE period_code LIKE 'C%'"
    ))


def downgrade() -> None:
    raise NotImplementedError("비가역 마이그레이션 — downgrade 불가")

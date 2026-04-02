# -*- coding: utf-8 -*-
"""add domain scope to product family options

Revision ID: 0053
Revises: 0052
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


_FAMILY_DOMAIN_MAP = {
    "fw": "sec",
    "ips": "sec",
    "waf": "sec",
    "ddos": "sec",
    "vpn": "sec",
    "siem": "sec",
    "soar": "sec",
    "dlp": "sec",
    "edr": "sec",
    "xdr": "sec",
    "iam": "sec",
    "pam": "sec",
    "pki": "sec",
    "proxy": "sec",
    "mail_security": "sec",
    "ztna": "sec",
    "nac": "sec",
    "l2": "net",
    "l3": "net",
    "l4": "net",
    "router": "net",
    "switch": "net",
    "adc": "net",
    "load_balancer": "net",
    "sdwan": "net",
    "dns": "net",
    "dhcp_ipam": "net",
    "nms": "net",
    "monitoring": "net",
    "x86_server": "svr",
    "unix_server": "svr",
    "blade_server": "svr",
    "virtualization": "svr",
    "container_platform": "svr",
    "hci": "svr",
    "vdi": "svr",
    "web_server": "svr",
    "was": "svr",
    "os": "svr",
    "middleware": "svr",
    "cache": "svr",
    "message_queue": "svr",
    "etl": "svr",
    "batch_scheduler": "svr",
    "devops": "svr",
    "nas": "sto",
    "san": "sto",
    "object_storage": "sto",
    "backup": "sto",
    "backup_sw": "sto",
    "dbms": "db",
    "db_replication": "db",
}


def _has_column(conn, table_name: str, column_name: str) -> bool:
    columns = inspect(conn).get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _attribute_id(conn, attribute_key: str) -> int | None:
    return conn.execute(
        sa.text("SELECT id FROM catalog_attribute_defs WHERE attribute_key = :attribute_key"),
        {"attribute_key": attribute_key},
    ).scalar()


def _option_id(conn, attribute_id: int, option_key: str) -> int | None:
    return conn.execute(
        sa.text(
            """
            SELECT id
            FROM catalog_attribute_options
            WHERE attribute_id = :attribute_id AND option_key = :option_key
            """
        ),
        {"attribute_id": attribute_id, "option_key": option_key},
    ).scalar()


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "catalog_attribute_options", "domain_option_id"):
        op.add_column("catalog_attribute_options", sa.Column("domain_option_id", sa.Integer(), nullable=True))
        op.create_index(
            "ix_catalog_attribute_options_domain_option_id",
            "catalog_attribute_options",
            ["domain_option_id"],
            unique=False,
        )
        op.create_foreign_key(
            "fk_catalog_attribute_options_domain_option_id",
            "catalog_attribute_options",
            "catalog_attribute_options",
            ["domain_option_id"],
            ["id"],
            ondelete="SET NULL",
        )

    product_family_attr_id = _attribute_id(conn, "product_family")
    domain_attr_id = _attribute_id(conn, "domain")
    if product_family_attr_id is None or domain_attr_id is None:
        return

    for family_key, domain_key in _FAMILY_DOMAIN_MAP.items():
        family_option_id = _option_id(conn, product_family_attr_id, family_key)
        domain_option_id = _option_id(conn, domain_attr_id, domain_key)
        if family_option_id is None or domain_option_id is None:
            continue
        conn.execute(
            sa.text(
                """
                UPDATE catalog_attribute_options
                SET domain_option_id = :domain_option_id
                WHERE id = :family_option_id
                  AND attribute_id = :product_family_attr_id
                """
            ),
            {
                "domain_option_id": domain_option_id,
                "family_option_id": family_option_id,
                "product_family_attr_id": product_family_attr_id,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "catalog_attribute_options", "domain_option_id"):
        return
    op.drop_constraint("fk_catalog_attribute_options_domain_option_id", "catalog_attribute_options", type_="foreignkey")
    op.drop_index("ix_catalog_attribute_options_domain_option_id", table_name="catalog_attribute_options")
    op.drop_column("catalog_attribute_options", "domain_option_id")

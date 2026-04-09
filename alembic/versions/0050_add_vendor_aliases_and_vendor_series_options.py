# -*- coding: utf-8 -*-
"""add vendor aliases and vendor series options

Revision ID: 0050
Revises: 0049
Create Date: 2026-03-30
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
import unicodedata

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


_SEPARATOR_RE = re.compile(r"[\s\-_./(),]+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-z가-힣]+")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").lower().strip()
    if not normalized:
        return ""
    normalized = _SEPARATOR_RE.sub("", normalized)
    normalized = _NON_ALNUM_RE.sub("", normalized)
    return normalized


def _has_table(conn, table_name: str) -> bool:
    return table_name in inspect(conn).get_table_names()


def _fetch_id(conn, sql: str, **params) -> int | None:
    row = conn.execute(sa.text(sql), params).fetchone()
    return None if row is None else int(row[0])


def _attribute_id(conn, attribute_key: str) -> int | None:
    return _fetch_id(
        conn,
        "SELECT id FROM catalog_attribute_defs WHERE attribute_key = :attribute_key",
        attribute_key=attribute_key,
    )


def _option_exists(conn, attribute_id: int, option_key: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                """
                SELECT 1 FROM catalog_attribute_options
                WHERE attribute_id = :attribute_id AND option_key = :option_key
                """
            ),
            {"attribute_id": attribute_id, "option_key": option_key},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    if not _has_table(conn, "catalog_vendor_aliases"):
        op.create_table(
            "catalog_vendor_aliases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("vendor_canonical", sa.String(length=100), nullable=False),
            sa.Column("alias_value", sa.String(length=100), nullable=False),
            sa.Column("normalized_alias", sa.String(length=120), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("normalized_alias", name="uq_catalog_vendor_alias_normalized"),
        )
        op.create_index("ix_catalog_vendor_aliases_vendor_canonical", "catalog_vendor_aliases", ["vendor_canonical"], unique=False)
        op.create_index("ix_catalog_vendor_aliases_normalized_alias", "catalog_vendor_aliases", ["normalized_alias"], unique=False)

    vendor_alias_seed = {
        "Palo Alto Networks": ["Palo Alto", "Paloalto", "팔로알토"],
        "Fortinet": ["forti net"],
        "Cisco": ["Cisco Systems", "시스코"],
        "Juniper": ["Juniper Networks", "주니퍼"],
        "A10 Networks": ["A10", "A10Networks"],
        "F5": ["F5 Networks"],
        "HPE": ["HP", "Hewlett Packard Enterprise"],
        "Dell EMC": ["DellEMC", "EMC"],
        "Red Hat": ["RedHat"],
        "NetApp": ["Net App"],
        "OpenAI": ["Open AI"],
        "IBM": ["International Business Machines"],
        "CrowdStrike": ["Crowd Strike"],
        "NGINX": ["Nginx"],
        "PostgreSQL": ["Postgres", "Postgre SQL"],
    }
    for canonical, aliases in vendor_alias_seed.items():
        for idx, alias in enumerate(aliases, start=1):
            normalized_alias = _normalize_text(alias)
            exists = conn.execute(
                sa.text(
                    """
                    SELECT 1
                    FROM catalog_vendor_aliases
                    WHERE normalized_alias = :normalized_alias
                    """
                ),
                {"normalized_alias": normalized_alias},
            ).scalar()
            if exists:
                continue
            conn.execute(
                sa.text(
                    """
                    INSERT INTO catalog_vendor_aliases (
                        vendor_canonical, alias_value, normalized_alias,
                        sort_order, is_active, created_at, updated_at
                    ) VALUES (
                        :vendor_canonical, :alias_value, :normalized_alias,
                        :sort_order, TRUE, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "vendor_canonical": canonical,
                    "alias_value": alias,
                    "normalized_alias": normalized_alias,
                    "sort_order": idx * 10,
                    "created_at": now,
                    "updated_at": now,
                },
            )

    vendor_series_attr_id = _attribute_id(conn, "vendor_series")
    if vendor_series_attr_id is not None:
        conn.execute(
            sa.text(
                """
                UPDATE catalog_attribute_defs
                   SET value_type = 'option',
                       updated_at = :updated_at
                 WHERE id = :attribute_id
                """
            ),
            {"attribute_id": vendor_series_attr_id, "updated_at": now},
        )
        vendor_series_options = [
            ("catalyst", "Catalyst"),
            ("nexus", "Nexus"),
            ("mx", "MX"),
            ("bigip", "BIG-IP"),
            ("thunder", "Thunder"),
            ("fortigate", "FortiGate"),
            ("pa_series", "PA Series"),
            ("srx", "SRX"),
            ("poweredge", "PowerEdge"),
            ("proliant", "ProLiant"),
            ("power", "Power"),
            ("fas", "FAS"),
            ("powerstore", "PowerStore"),
            ("flasharray", "FlashArray"),
            ("windows_server", "Windows Server"),
            ("sql_server", "SQL Server"),
            ("oracle_database", "Oracle Database"),
            ("exadata", "Exadata"),
            ("rhel", "RHEL"),
            ("vsphere", "vSphere"),
            ("splunk_enterprise", "Splunk Enterprise"),
            ("falcon", "Falcon"),
            ("openshift", "OpenShift"),
            ("nginx_plus", "NGINX Plus"),
        ]
        for idx, (option_key, label) in enumerate(vendor_series_options, start=1):
            if _option_exists(conn, vendor_series_attr_id, option_key):
                continue
            conn.execute(
                sa.text(
                    """
                    INSERT INTO catalog_attribute_options (
                        attribute_id, option_key, label, description,
                        sort_order, is_active, created_at, updated_at
                    ) VALUES (
                        :attribute_id, :option_key, :label, NULL,
                        :sort_order, TRUE, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "attribute_id": vendor_series_attr_id,
                    "option_key": option_key,
                    "label": label,
                    "sort_order": idx * 10,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    vendor_series_attr_id = _attribute_id(conn, "vendor_series")
    if vendor_series_attr_id is not None:
        conn.execute(
            sa.text(
                """
                UPDATE catalog_attribute_defs
                   SET value_type = 'text'
                 WHERE id = :attribute_id
                """
            ),
            {"attribute_id": vendor_series_attr_id},
        )
        for option_key in (
            "catalyst", "nexus", "mx", "bigip", "thunder", "fortigate", "pa_series",
            "srx", "poweredge", "proliant", "power", "fas", "powerstore", "flasharray",
            "windows_server", "sql_server", "oracle_database", "exadata", "rhel",
            "vsphere", "splunk_enterprise", "falcon", "openshift", "nginx_plus",
        ):
            conn.execute(
                sa.text(
                    """
                    DELETE FROM catalog_attribute_options
                    WHERE attribute_id = :attribute_id AND option_key = :option_key
                    """
                ),
                {"attribute_id": vendor_series_attr_id, "option_key": option_key},
            )

    if _has_table(conn, "catalog_vendor_aliases"):
        op.drop_index("ix_catalog_vendor_aliases_normalized_alias", table_name="catalog_vendor_aliases")
        op.drop_index("ix_catalog_vendor_aliases_vendor_canonical", table_name="catalog_vendor_aliases")
        op.drop_table("catalog_vendor_aliases")

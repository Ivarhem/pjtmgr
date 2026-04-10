# -*- coding: utf-8 -*-
"""seed common catalog products

Revision ID: 0049
Revises: 0048
Create Date: 2026-03-30
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "0049"
down_revision = "0048"
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


def _attribute_id_map(conn) -> dict[str, int]:
    rows = conn.execute(
        sa.text(
            """
            SELECT id, attribute_key
            FROM catalog_attribute_defs
            WHERE attribute_key IN ('domain', 'imp_type', 'product_family', 'platform')
            """
        )
    ).mappings().all()
    return {row["attribute_key"]: int(row["id"]) for row in rows}


def _option_id_map(conn) -> dict[tuple[str, str], int]:
    rows = conn.execute(
        sa.text(
            """
            SELECT d.attribute_key, o.option_key, o.id
            FROM catalog_attribute_options o
            JOIN catalog_attribute_defs d ON d.id = o.attribute_id
            WHERE d.attribute_key IN ('domain', 'imp_type', 'product_family', 'platform')
            """
        )
    ).mappings().all()
    return {(row["attribute_key"], row["option_key"]): int(row["id"]) for row in rows}


def _product_exists(conn, vendor: str, name: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                """
                SELECT 1
                FROM product_catalog
                WHERE vendor = :vendor AND name = :name
                """
            ),
            {"vendor": vendor, "name": name},
        ).scalar()
    )


def _insert_product(conn, product: dict[str, str | None], now: datetime) -> int:
    row = conn.execute(
        sa.text(
            """
            INSERT INTO product_catalog (
                vendor, name, product_type, version, reference_url,
                normalized_vendor, normalized_name, is_placeholder,
                created_at, updated_at
            ) VALUES (
                :vendor, :name, :product_type, :version, :reference_url,
                :normalized_vendor, :normalized_name, FALSE,
                :created_at, :updated_at
            )
            RETURNING id
            """
        ),
        {
            "vendor": product["vendor"],
            "name": product["name"],
            "product_type": product["product_type"],
            "version": product.get("version"),
            "reference_url": product.get("reference_url"),
            "normalized_vendor": _normalize_text(product["vendor"]),
            "normalized_name": _normalize_text(product["name"]),
            "created_at": now,
            "updated_at": now,
        },
    ).scalar_one()
    return int(row)


def _insert_attribute_value(conn, *, product_id: int, attribute_id: int, option_id: int, now: datetime) -> None:
    conn.execute(
        sa.text(
            """
            INSERT INTO product_catalog_attribute_values (
                product_id, attribute_id, option_id, raw_value,
                sort_order, is_primary, created_at, updated_at
            ) VALUES (
                :product_id, :attribute_id, :option_id, NULL,
                100, TRUE, :created_at, :updated_at
            )
            """
        ),
        {
            "product_id": product_id,
            "attribute_id": attribute_id,
            "option_id": option_id,
            "created_at": now,
            "updated_at": now,
        },
    )


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()
    attribute_ids = _attribute_id_map(conn)
    option_ids = _option_id_map(conn)

    products = [
        {"vendor": "Cisco", "name": "Nexus 93180YC-FX3", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "l3", "platform": "appliance"},
        {"vendor": "Juniper", "name": "MX204", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "router", "platform": "appliance"},
        {"vendor": "F5", "name": "BIG-IP i5800", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "adc", "platform": "appliance"},
        {"vendor": "A10 Networks", "name": "Thunder 1040S", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "adc", "platform": "appliance"},
        {"vendor": "Cisco", "name": "Catalyst 8300", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "sdwan", "platform": "appliance"},
        {"vendor": "Infoblox", "name": "NIOS DDI", "product_type": "software", "domain": "net", "imp_type": "sw", "product_family": "dhcp_ipam", "platform": "linux"},
        {"vendor": "SolarWinds", "name": "Network Performance Monitor", "product_type": "software", "domain": "net", "imp_type": "sw", "product_family": "monitoring", "platform": "windows"},
        {"vendor": "Palo Alto Networks", "name": "PA-3220", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "fw", "platform": "appliance"},
        {"vendor": "Fortinet", "name": "FortiGate 200F", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "fw", "platform": "appliance"},
        {"vendor": "Imperva", "name": "SecureSphere X2500", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "waf", "platform": "appliance"},
        {"vendor": "Trend Micro", "name": "TippingPoint TPS 4400TX", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "ips", "platform": "appliance"},
        {"vendor": "Pulse Secure", "name": "PSA 3000", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "vpn", "platform": "appliance"},
        {"vendor": "Palo Alto Networks", "name": "Prisma Access", "product_type": "service", "domain": "sec", "imp_type": "svc", "product_family": "ztna", "platform": None},
        {"vendor": "CrowdStrike", "name": "Falcon Insight XDR", "product_type": "service", "domain": "sec", "imp_type": "svc", "product_family": "xdr", "platform": None},
        {"vendor": "Splunk", "name": "Splunk Enterprise", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "siem", "platform": "linux"},
        {"vendor": "Symantec", "name": "Data Loss Prevention", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "dlp", "platform": "windows"},
        {"vendor": "Okta", "name": "Workforce Identity Cloud", "product_type": "service", "domain": "sec", "imp_type": "svc", "product_family": "iam", "platform": None},
        {"vendor": "Cisco", "name": "Identity Services Engine", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "nac", "platform": "linux"},
        {"vendor": "Dell", "name": "PowerEdge R760", "product_type": "hardware", "domain": "svr", "imp_type": "hw", "product_family": "x86_server", "platform": "x86"},
        {"vendor": "IBM", "name": "Power E1080", "product_type": "hardware", "domain": "svr", "imp_type": "hw", "product_family": "unix_server", "platform": "unix"},
        {"vendor": "Red Hat", "name": "Enterprise Linux 9", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "os", "platform": "linux"},
        {"vendor": "Microsoft", "name": "Windows Server 2025", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "os", "platform": "windows"},
        {"vendor": "VMware", "name": "vSphere 8", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "virtualization", "platform": "vm"},
        {"vendor": "Apache", "name": "HTTP Server 2.4", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "web_server", "platform": "linux"},
        {"vendor": "NGINX", "name": "NGINX Plus", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "web_server", "platform": "linux"},
        {"vendor": "Apache", "name": "Tomcat 10", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "was", "platform": "linux"},
        {"vendor": "Veeam", "name": "Backup & Replication 12", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "backup_sw", "platform": "windows"},
        {"vendor": "IBM", "name": "MQ 9.4", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "message_queue", "platform": "linux"},
        {"vendor": "Red Hat", "name": "OpenShift Container Platform 4", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "container_platform", "platform": "container"},
        {"vendor": "NetApp", "name": "FAS2750", "product_type": "hardware", "domain": "sto", "imp_type": "hw", "product_family": "nas", "platform": "appliance"},
        {"vendor": "Dell EMC", "name": "PowerStore 500T", "product_type": "hardware", "domain": "sto", "imp_type": "hw", "product_family": "san", "platform": "appliance"},
        {"vendor": "Pure Storage", "name": "FlashArray X20", "product_type": "hardware", "domain": "sto", "imp_type": "hw", "product_family": "san", "platform": "appliance"},
        {"vendor": "MinIO", "name": "Enterprise Object Store", "product_type": "software", "domain": "sto", "imp_type": "sw", "product_family": "object_storage", "platform": "linux"},
        {"vendor": "Oracle", "name": "Exadata X10M", "product_type": "hardware", "domain": "db", "imp_type": "hw", "product_family": "dbms", "platform": "appliance"},
        {"vendor": "Microsoft", "name": "SQL Server 2022", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "dbms", "platform": "windows"},
        {"vendor": "PostgreSQL", "name": "PostgreSQL 16", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "dbms", "platform": "linux"},
        {"vendor": "MySQL", "name": "MySQL Enterprise 8.4", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "dbms", "platform": "linux"},
        {"vendor": "OpenAI", "name": "GPT-4.1 mini", "product_type": "model", "domain": "sec", "imp_type": "svc", "product_family": "generic", "platform": None},
    ]

    for product in products:
        if _product_exists(conn, product["vendor"], product["name"]):
            continue
        product_id = _insert_product(conn, product, now)
        for attribute_key in ("domain", "imp_type", "product_family", "platform"):
            option_key = product.get(attribute_key)
            if not option_key:
                continue
            attribute_id = attribute_ids.get(attribute_key)
            option_id = option_ids.get((attribute_key, option_key))
            if not attribute_id or not option_id:
                raise RuntimeError(f"Missing seed option for {attribute_key}:{option_key}")
            _insert_attribute_value(
                conn,
                product_id=product_id,
                attribute_id=attribute_id,
                option_id=option_id,
                now=now,
            )


def downgrade() -> None:
    conn = op.get_bind()
    product_keys = [
        ("Cisco", "Nexus 93180YC-FX3"),
        ("Juniper", "MX204"),
        ("F5", "BIG-IP i5800"),
        ("A10 Networks", "Thunder 1040S"),
        ("Cisco", "Catalyst 8300"),
        ("Infoblox", "NIOS DDI"),
        ("SolarWinds", "Network Performance Monitor"),
        ("Palo Alto Networks", "PA-3220"),
        ("Fortinet", "FortiGate 200F"),
        ("Imperva", "SecureSphere X2500"),
        ("Trend Micro", "TippingPoint TPS 4400TX"),
        ("Pulse Secure", "PSA 3000"),
        ("Palo Alto Networks", "Prisma Access"),
        ("CrowdStrike", "Falcon Insight XDR"),
        ("Splunk", "Splunk Enterprise"),
        ("Symantec", "Data Loss Prevention"),
        ("Okta", "Workforce Identity Cloud"),
        ("Cisco", "Identity Services Engine"),
        ("Dell", "PowerEdge R760"),
        ("IBM", "Power E1080"),
        ("Red Hat", "Enterprise Linux 9"),
        ("Microsoft", "Windows Server 2025"),
        ("VMware", "vSphere 8"),
        ("Apache", "HTTP Server 2.4"),
        ("NGINX", "NGINX Plus"),
        ("Apache", "Tomcat 10"),
        ("Veeam", "Backup & Replication 12"),
        ("IBM", "MQ 9.4"),
        ("Red Hat", "OpenShift Container Platform 4"),
        ("NetApp", "FAS2750"),
        ("Dell EMC", "PowerStore 500T"),
        ("Pure Storage", "FlashArray X20"),
        ("MinIO", "Enterprise Object Store"),
        ("Oracle", "Exadata X10M"),
        ("Microsoft", "SQL Server 2022"),
        ("PostgreSQL", "PostgreSQL 16"),
        ("MySQL", "MySQL Enterprise 8.4"),
        ("OpenAI", "GPT-4.1 mini"),
    ]
    for vendor, name in product_keys:
        conn.execute(
            sa.text(
                """
                DELETE FROM product_catalog
                WHERE vendor = :vendor AND name = :name
                """
            ),
            {"vendor": vendor, "name": name},
        )

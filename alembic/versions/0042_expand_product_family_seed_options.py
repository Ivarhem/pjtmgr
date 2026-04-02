# -*- coding: utf-8 -*-
"""Expand product family seed options.

Revision ID: 0042
Revises: 0041
Create Date: 2026-03-30
"""

from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _fetch_id(conn, sql: str, **params) -> int | None:
    row = conn.execute(sa.text(sql), params).fetchone()
    return None if row is None else int(row[0])


def _attribute_id(conn, attribute_key: str) -> int | None:
    return _fetch_id(
        conn,
        "SELECT id FROM catalog_attribute_defs WHERE attribute_key = :attribute_key",
        attribute_key=attribute_key,
    )


def _option_id(conn, attribute_id: int, option_key: str) -> int | None:
    return _fetch_id(
        conn,
        """
        SELECT id
        FROM catalog_attribute_options
        WHERE attribute_id = :attribute_id
          AND option_key = :option_key
        """,
        attribute_id=attribute_id,
        option_key=option_key,
    )


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()
    attribute_id = _attribute_id(conn, "product_family")
    if attribute_id is None:
        raise RuntimeError("product_family attribute not found")

    options = [
        ("utm", "UTM"),
        ("ids", "IDS"),
        ("vpn", "VPN"),
        ("router", "라우터"),
        ("switch", "스위치"),
        ("adc", "ADC"),
        ("load_balancer", "로드밸런서"),
        ("sdwan", "SD-WAN"),
        ("dns", "DNS"),
        ("dhcp_ipam", "DHCP/IPAM"),
        ("monitoring", "모니터링"),
        ("soar", "SOAR"),
        ("dlp", "DLP"),
        ("edr", "EDR"),
        ("xdr", "XDR"),
        ("iam", "IAM"),
        ("pam", "PAM"),
        ("pki", "PKI"),
        ("proxy", "프록시"),
        ("mail_security", "메일 보안"),
        ("ztna", "ZTNA"),
        ("nac", "NAC"),
        ("blade_server", "블레이드 서버"),
        ("virtualization", "가상화"),
        ("container_platform", "컨테이너 플랫폼"),
        ("hci", "HCI"),
        ("vdi", "VDI"),
        ("object_storage", "오브젝트 스토리지"),
        ("db_replication", "DB 복제"),
        ("web_server", "웹 서버"),
        ("was", "WAS"),
        ("backup_sw", "백업 소프트웨어"),
        ("cache", "캐시"),
        ("message_queue", "메시지 큐"),
        ("etl", "ETL"),
        ("batch_scheduler", "배치 스케줄러"),
        ("devops", "DevOps 도구"),
    ]

    base_sort = conn.execute(
        sa.text(
            """
            SELECT COALESCE(MAX(sort_order), 0)
            FROM catalog_attribute_options
            WHERE attribute_id = :attribute_id
            """
        ),
        {"attribute_id": attribute_id},
    ).scalar_one()
    next_sort = int(base_sort) + 10

    for option_key, label in options:
        if _option_id(conn, attribute_id, option_key) is not None:
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
                "attribute_id": attribute_id,
                "option_key": option_key,
                "label": label,
                "sort_order": next_sort,
                "created_at": now,
                "updated_at": now,
            },
        )
        next_sort += 10


def downgrade() -> None:
    conn = op.get_bind()
    attribute_id = _attribute_id(conn, "product_family")
    if attribute_id is None:
        return
    option_keys = [
        "utm",
        "ids",
        "vpn",
        "router",
        "switch",
        "adc",
        "load_balancer",
        "sdwan",
        "dns",
        "dhcp_ipam",
        "monitoring",
        "soar",
        "dlp",
        "edr",
        "xdr",
        "iam",
        "pam",
        "pki",
        "proxy",
        "mail_security",
        "ztna",
        "nac",
        "blade_server",
        "virtualization",
        "container_platform",
        "hci",
        "vdi",
        "object_storage",
        "db_replication",
        "web_server",
        "was",
        "backup_sw",
        "cache",
        "message_queue",
        "etl",
        "batch_scheduler",
        "devops",
    ]
    for option_key in option_keys:
        conn.execute(
            sa.text(
                """
                DELETE FROM catalog_attribute_options
                WHERE attribute_id = :attribute_id
                  AND option_key = :option_key
                """
            ),
            {"attribute_id": attribute_id, "option_key": option_key},
        )

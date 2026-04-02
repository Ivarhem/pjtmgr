# -*- coding: utf-8 -*-
"""Seed catalog attributes, layouts, and identity rules.

Revision ID: 0037
Revises: 0036
Create Date: 2026-03-27
"""

from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0037"
down_revision = "0036"
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


def _option_id(conn, attribute_key: str, option_key: str) -> int | None:
    return _fetch_id(
        conn,
        """
        SELECT o.id
        FROM catalog_attribute_options o
        JOIN catalog_attribute_defs a ON a.id = o.attribute_id
        WHERE a.attribute_key = :attribute_key
          AND o.option_key = :option_key
        """,
        attribute_key=attribute_key,
        option_key=option_key,
    )


def _layout_id(conn, scope_type: str, name: str) -> int | None:
    return _fetch_id(
        conn,
        """
        SELECT id
        FROM classification_layouts
        WHERE scope_type = :scope_type
          AND name = :name
        """,
        scope_type=scope_type,
        name=name,
    )


def _level_id(conn, layout_id: int, level_no: int) -> int | None:
    return _fetch_id(
        conn,
        """
        SELECT id
        FROM classification_layout_levels
        WHERE layout_id = :layout_id
          AND level_no = :level_no
        """,
        layout_id=layout_id,
        level_no=level_no,
    )


def _ensure_attribute(conn, payload: dict) -> int:
    attribute_id = _attribute_id(conn, payload["attribute_key"])
    if attribute_id is not None:
        return attribute_id
    conn.execute(
        sa.text(
            """
            INSERT INTO catalog_attribute_defs (
                attribute_key, label, description, value_type,
                is_required, is_display_required, is_displayable,
                is_system, multi_value, sort_order, is_active,
                created_at, updated_at
            ) VALUES (
                :attribute_key, :label, :description, :value_type,
                :is_required, :is_display_required, :is_displayable,
                :is_system, :multi_value, :sort_order, :is_active,
                :created_at, :updated_at
            )
            """
        ),
        payload,
    )
    attribute_id = _attribute_id(conn, payload["attribute_key"])
    assert attribute_id is not None
    return attribute_id


def _ensure_option(conn, attribute_id: int, attribute_key: str, payload: dict) -> int:
    option_id = _option_id(conn, attribute_key, payload["option_key"])
    if option_id is not None:
        return option_id
    conn.execute(
        sa.text(
            """
            INSERT INTO catalog_attribute_options (
                attribute_id, option_key, label, description,
                sort_order, is_active, created_at, updated_at
            ) VALUES (
                :attribute_id, :option_key, :label, :description,
                :sort_order, :is_active, :created_at, :updated_at
            )
            """
        ),
        {"attribute_id": attribute_id, **payload},
    )
    option_id = _option_id(conn, attribute_key, payload["option_key"])
    assert option_id is not None
    return option_id


def _ensure_layout(conn, payload: dict) -> int:
    layout_id = _layout_id(conn, payload["scope_type"], payload["name"])
    if layout_id is not None:
        return layout_id
    conn.execute(
        sa.text(
            """
            INSERT INTO classification_layouts (
                scope_type, project_id, name, description,
                depth_count, is_default, is_active,
                created_at, updated_at
            ) VALUES (
                :scope_type, :project_id, :name, :description,
                :depth_count, :is_default, :is_active,
                :created_at, :updated_at
            )
            """
        ),
        payload,
    )
    layout_id = _layout_id(conn, payload["scope_type"], payload["name"])
    assert layout_id is not None
    return layout_id


def _ensure_level(conn, layout_id: int, payload: dict) -> int:
    level_id = _level_id(conn, layout_id, payload["level_no"])
    if level_id is not None:
        return level_id
    conn.execute(
        sa.text(
            """
            INSERT INTO classification_layout_levels (
                layout_id, level_no, alias, joiner, prefix_mode,
                sort_order, created_at, updated_at
            ) VALUES (
                :layout_id, :level_no, :alias, :joiner, :prefix_mode,
                :sort_order, :created_at, :updated_at
            )
            """
        ),
        {"layout_id": layout_id, **payload},
    )
    level_id = _level_id(conn, layout_id, payload["level_no"])
    assert level_id is not None
    return level_id


def _ensure_level_key(conn, level_id: int, attribute_id: int, payload: dict) -> None:
    exists = _fetch_id(
        conn,
        """
        SELECT id
        FROM classification_layout_level_keys
        WHERE level_id = :level_id
          AND attribute_id = :attribute_id
        """,
        level_id=level_id,
        attribute_id=attribute_id,
    )
    if exists is not None:
        return
    conn.execute(
        sa.text(
            """
            INSERT INTO classification_layout_level_keys (
                level_id, attribute_id, sort_order, is_visible,
                created_at, updated_at
            ) VALUES (
                :level_id, :attribute_id, :sort_order, :is_visible,
                :created_at, :updated_at
            )
            """
        ),
        {"level_id": level_id, "attribute_id": attribute_id, **payload},
    )


def _ensure_identity_rule(conn, payload: dict) -> None:
    exists = _fetch_id(
        conn,
        """
        SELECT id
        FROM asset_identity_rules
        WHERE COALESCE(domain_option_id, -1) = COALESCE(:domain_option_id, -1)
          AND COALESCE(imp_type_option_id, -1) = COALESCE(:imp_type_option_id, -1)
          AND COALESCE(product_family_option_id, -1) = COALESCE(:product_family_option_id, -1)
          AND COALESCE(platform_option_id, -1) = COALESCE(:platform_option_id, -1)
          AND asset_type_code = :asset_type_code
        """,
        **payload,
    )
    if exists is not None:
        return
    conn.execute(
        sa.text(
            """
            INSERT INTO asset_identity_rules (
                domain_option_id, imp_type_option_id, product_family_option_id, platform_option_id,
                asset_type_code, asset_type_label, priority, is_active,
                created_at, updated_at
            ) VALUES (
                :domain_option_id, :imp_type_option_id, :product_family_option_id, :platform_option_id,
                :asset_type_code, :asset_type_label, :priority, :is_active,
                :created_at, :updated_at
            )
            """
        ),
        payload,
    )


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    attributes = [
        {
            "attribute_key": "domain",
            "label": "도메인",
            "description": "담당 영역 축",
            "value_type": "option",
            "is_required": True,
            "is_display_required": True,
            "is_displayable": True,
            "is_system": True,
            "multi_value": False,
            "sort_order": 10,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "attribute_key": "imp_type",
            "label": "구현형태",
            "description": "HW/SW/SVC",
            "value_type": "option",
            "is_required": True,
            "is_display_required": False,
            "is_displayable": True,
            "is_system": True,
            "multi_value": False,
            "sort_order": 20,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "attribute_key": "product_family",
            "label": "제품군",
            "description": "방화벽, IPS, OS, DBMS 등 제품 계열",
            "value_type": "option",
            "is_required": False,
            "is_display_required": False,
            "is_displayable": True,
            "is_system": True,
            "multi_value": False,
            "sort_order": 30,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "attribute_key": "platform",
            "label": "플랫폼",
            "description": "appliance, x86, windows 등",
            "value_type": "option",
            "is_required": False,
            "is_display_required": False,
            "is_displayable": True,
            "is_system": True,
            "multi_value": False,
            "sort_order": 40,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "attribute_key": "deployment_model",
            "label": "배치형태",
            "description": "on-prem, SaaS, managed",
            "value_type": "option",
            "is_required": False,
            "is_display_required": False,
            "is_displayable": True,
            "is_system": True,
            "multi_value": False,
            "sort_order": 50,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "attribute_key": "vendor_series",
            "label": "제품시리즈",
            "description": "벤더 제품 시리즈명",
            "value_type": "text",
            "is_required": False,
            "is_display_required": False,
            "is_displayable": True,
            "is_system": True,
            "multi_value": False,
            "sort_order": 60,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "attribute_key": "license_model",
            "label": "라이선스형태",
            "description": "subscription, perpetual 등",
            "value_type": "option",
            "is_required": False,
            "is_display_required": False,
            "is_displayable": True,
            "is_system": True,
            "multi_value": False,
            "sort_order": 70,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]
    attribute_ids = {
        payload["attribute_key"]: _ensure_attribute(conn, payload)
        for payload in attributes
    }

    option_seed = {
        "domain": [
            ("net", "네트워크"),
            ("sec", "보안"),
            ("svr", "서버"),
            ("sto", "스토리지"),
            ("db", "데이터베이스"),
        ],
        "imp_type": [
            ("hw", "하드웨어"),
            ("sw", "소프트웨어"),
            ("svc", "서비스"),
        ],
        "product_family": [
            ("fw", "방화벽"),
            ("utm", "UTM"),
            ("ips", "IPS"),
            ("ids", "IDS"),
            ("waf", "WAF"),
            ("ddos", "DDoS"),
            ("vpn", "VPN"),
            ("l2", "L2 스위치"),
            ("l3", "L3 스위치"),
            ("l4", "L4"),
            ("router", "라우터"),
            ("switch", "스위치"),
            ("adc", "ADC"),
            ("load_balancer", "로드밸런서"),
            ("sdwan", "SD-WAN"),
            ("dns", "DNS"),
            ("dhcp_ipam", "DHCP/IPAM"),
            ("nms", "NMS"),
            ("monitoring", "모니터링"),
            ("siem", "SIEM"),
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
            ("x86_server", "x86 서버"),
            ("unix_server", "UNIX 서버"),
            ("blade_server", "블레이드 서버"),
            ("virtualization", "가상화"),
            ("container_platform", "컨테이너 플랫폼"),
            ("hci", "HCI"),
            ("vdi", "VDI"),
            ("nas", "NAS"),
            ("san", "SAN"),
            ("object_storage", "오브젝트 스토리지"),
            ("dbms", "DBMS"),
            ("db_replication", "DB 복제"),
            ("web_server", "웹 서버"),
            ("was", "WAS"),
            ("os", "OS"),
            ("backup", "백업"),
            ("backup_sw", "백업 소프트웨어"),
            ("middleware", "미들웨어"),
            ("cache", "캐시"),
            ("message_queue", "메시지 큐"),
            ("etl", "ETL"),
            ("batch_scheduler", "배치 스케줄러"),
            ("devops", "DevOps 도구"),
            ("generic", "기타"),
        ],
        "platform": [
            ("appliance", "Appliance"),
            ("x86", "x86"),
            ("windows", "Windows"),
            ("linux", "Linux"),
            ("unix", "UNIX"),
            ("vm", "VM"),
            ("container", "Container"),
        ],
        "deployment_model": [
            ("onprem", "On-Prem"),
            ("saas", "SaaS"),
            ("managed", "Managed Service"),
        ],
        "license_model": [
            ("perpetual", "Perpetual"),
            ("subscription", "Subscription"),
            ("capacity", "Capacity"),
            ("user_based", "User Based"),
        ],
    }
    for attribute_key, options in option_seed.items():
        for idx, (option_key, label) in enumerate(options, start=1):
            _ensure_option(
                conn,
                attribute_ids[attribute_key],
                attribute_key,
                {
                    "option_key": option_key,
                    "label": label,
                    "description": None,
                    "sort_order": idx * 10,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                },
            )

    layouts = [
        {
            "scope_type": "global",
            "project_id": None,
            "name": "기술기준형",
            "description": "도메인 > 구현형태 > 제품군 > 플랫폼 기준 기본 분류",
            "depth_count": 4,
            "is_default": True,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "levels": [
                {"level_no": 1, "alias": "대분류", "joiner": ", ", "prefix_mode": None, "sort_order": 10},
                {"level_no": 2, "alias": "중분류", "joiner": ", ", "prefix_mode": None, "sort_order": 20},
                {"level_no": 3, "alias": "소분류", "joiner": ", ", "prefix_mode": None, "sort_order": 30},
                {"level_no": 4, "alias": "세구분", "joiner": ", ", "prefix_mode": None, "sort_order": 40},
            ],
            "keys": {
                1: [("domain", 10)],
                2: [("imp_type", 10)],
                3: [("product_family", 10)],
                4: [("platform", 10)],
            },
        },
        {
            "scope_type": "global",
            "project_id": None,
            "name": "제품군우선형",
            "description": "도메인 > 제품군 > 구현형태 > 플랫폼 기준 분류",
            "depth_count": 4,
            "is_default": False,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "levels": [
                {"level_no": 1, "alias": "대분류", "joiner": ", ", "prefix_mode": None, "sort_order": 10},
                {"level_no": 2, "alias": "중분류", "joiner": ", ", "prefix_mode": None, "sort_order": 20},
                {"level_no": 3, "alias": "소분류", "joiner": ", ", "prefix_mode": None, "sort_order": 30},
                {"level_no": 4, "alias": "세구분", "joiner": ", ", "prefix_mode": None, "sort_order": 40},
            ],
            "keys": {
                1: [("domain", 10)],
                2: [("product_family", 10)],
                3: [("imp_type", 10)],
                4: [("platform", 10)],
            },
        },
    ]
    for layout_payload in layouts:
        layout_id = _ensure_layout(
            conn,
            {
                key: layout_payload[key]
                for key in (
                    "scope_type",
                    "project_id",
                    "name",
                    "description",
                    "depth_count",
                    "is_default",
                    "is_active",
                    "created_at",
                    "updated_at",
                )
            },
        )
        for level_payload in layout_payload["levels"]:
            level_id = _ensure_level(
                conn,
                layout_id,
                {**level_payload, "created_at": now, "updated_at": now},
            )
            for attribute_key, sort_order in layout_payload["keys"][level_payload["level_no"]]:
                _ensure_level_key(
                    conn,
                    level_id,
                    attribute_ids[attribute_key],
                    {
                        "sort_order": sort_order,
                        "is_visible": True,
                        "created_at": now,
                        "updated_at": now,
                    },
                )

    rules = [
        ("sec", None, "fw", None, "FW", "방화벽"),
        ("sec", None, "ips", None, "IPS", "침입방지시스템"),
        ("sec", None, "waf", None, "WAF", "웹방화벽"),
        ("net", None, "l2", None, "L2", "L2 스위치"),
        ("net", None, "l3", None, "L3", "L3 스위치"),
        ("net", None, "l4", None, "L4", "L4"),
        ("svr", None, "x86_server", None, "SVR", "서버"),
        ("sto", None, "nas", None, "NAS", "NAS"),
        ("sto", None, "san", None, "SAN", "SAN"),
        ("db", None, "dbms", None, "DB", "DBMS"),
    ]
    for domain_key, imp_type_key, family_key, platform_key, code, label in rules:
        _ensure_identity_rule(
            conn,
            {
                "domain_option_id": _option_id(conn, "domain", domain_key),
                "imp_type_option_id": _option_id(conn, "imp_type", imp_type_key) if imp_type_key else None,
                "product_family_option_id": _option_id(conn, "product_family", family_key) if family_key else None,
                "platform_option_id": _option_id(conn, "platform", platform_key) if platform_key else None,
                "asset_type_code": code,
                "asset_type_label": label,
                "priority": 100,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DELETE FROM asset_identity_rules
            WHERE asset_type_code IN ('FW', 'IPS', 'WAF', 'L2', 'L3', 'L4', 'SVR', 'NAS', 'SAN', 'DB')
            """
        )
    )

    conn.execute(
        sa.text(
            """
            DELETE FROM classification_layout_level_keys
            WHERE level_id IN (
                SELECT l.id
                FROM classification_layout_levels l
                JOIN classification_layouts h ON h.id = l.layout_id
                WHERE h.scope_type = 'global'
                  AND h.name IN ('기술기준형', '제품군우선형')
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM classification_layout_levels
            WHERE layout_id IN (
                SELECT id
                FROM classification_layouts
                WHERE scope_type = 'global'
                  AND name IN ('기술기준형', '제품군우선형')
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM classification_layouts
            WHERE scope_type = 'global'
              AND name IN ('기술기준형', '제품군우선형')
            """
        )
    )

    conn.execute(
        sa.text(
            """
            DELETE FROM catalog_attribute_options
            WHERE attribute_id IN (
                SELECT id
                FROM catalog_attribute_defs
                WHERE attribute_key IN (
                    'domain', 'imp_type', 'product_family', 'platform',
                    'deployment_model', 'vendor_series', 'license_model'
                )
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM catalog_attribute_defs
            WHERE attribute_key IN (
                'domain', 'imp_type', 'product_family', 'platform',
                'deployment_model', 'vendor_series', 'license_model'
            )
            """
        )
    )

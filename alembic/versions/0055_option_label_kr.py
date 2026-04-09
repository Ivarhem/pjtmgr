# -*- coding: utf-8 -*-
"""add label_kr column to catalog_attribute_options with backfill

Revision ID: 0055
Revises: 0054
Create Date: 2026-04-02
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "0055"
down_revision = "0054"
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


# ─────────────────────────────────────────────
# BACKFILL_MAP: (attribute_key, option_key) -> {label: English, label_kr: Korean or None}
# ─────────────────────────────────────────────

BACKFILL_MAP: dict[tuple[str, str], dict[str, str | None]] = {
    # domain
    ("domain", "net"): {"label": "Network", "label_kr": "네트워크"},
    ("domain", "sec"): {"label": "Security", "label_kr": "보안"},
    ("domain", "svr"): {"label": "Server", "label_kr": "서버"},
    ("domain", "sto"): {"label": "Storage", "label_kr": "스토리지"},
    ("domain", "db"): {"label": "Database", "label_kr": "데이터베이스"},
    ("domain", "generic"): {"label": "Generic", "label_kr": None},
    ("domain", "app"): {"label": "Application", "label_kr": "애플리케이션"},

    # imp_type
    ("imp_type", "hw"): {"label": "Hardware", "label_kr": "하드웨어"},
    ("imp_type", "sw"): {"label": "Software", "label_kr": "소프트웨어"},
    ("imp_type", "svc"): {"label": "Service", "label_kr": "서비스"},

    # platform — all already English
    ("platform", "appliance"): {"label": "Appliance", "label_kr": None},
    ("platform", "x86"): {"label": "x86", "label_kr": None},
    ("platform", "windows"): {"label": "Windows", "label_kr": None},
    ("platform", "linux"): {"label": "Linux", "label_kr": None},
    ("platform", "unix"): {"label": "UNIX", "label_kr": None},
    ("platform", "vm"): {"label": "VM", "label_kr": None},
    ("platform", "container"): {"label": "Container", "label_kr": None},
    ("platform", "cloud"): {"label": "Cloud", "label_kr": None},
    ("platform", "virtual_appliance"): {"label": "Virtual Appliance", "label_kr": None},

    # deployment_model
    ("deployment_model", "onprem"): {"label": "On-Prem", "label_kr": "온프레미스"},
    ("deployment_model", "saas"): {"label": "SaaS", "label_kr": None},
    ("deployment_model", "managed"): {"label": "Managed Service", "label_kr": None},
    ("deployment_model", "hybrid"): {"label": "Hybrid", "label_kr": None},
    ("deployment_model", "paas"): {"label": "PaaS", "label_kr": None},

    # license_model
    ("license_model", "perpetual"): {"label": "Perpetual", "label_kr": "영구"},
    ("license_model", "subscription"): {"label": "Subscription", "label_kr": "구독"},
    ("license_model", "capacity"): {"label": "Capacity", "label_kr": "용량기반"},
    ("license_model", "user_based"): {"label": "User Based", "label_kr": "사용자기반"},
    ("license_model", "open_source"): {"label": "Open Source", "label_kr": "오픈소스"},
    ("license_model", "freemium"): {"label": "Freemium", "label_kr": None},
    ("license_model", "metered"): {"label": "Metered", "label_kr": "종량제"},

    # vendor_series — all already English
    ("vendor_series", "catalyst"): {"label": "Catalyst", "label_kr": None},
    ("vendor_series", "nexus"): {"label": "Nexus", "label_kr": None},
    ("vendor_series", "mx"): {"label": "MX", "label_kr": None},
    ("vendor_series", "bigip"): {"label": "BIG-IP", "label_kr": None},
    ("vendor_series", "thunder"): {"label": "Thunder", "label_kr": None},
    ("vendor_series", "fortigate"): {"label": "FortiGate", "label_kr": None},
    ("vendor_series", "pa_series"): {"label": "PA Series", "label_kr": None},
    ("vendor_series", "srx"): {"label": "SRX", "label_kr": None},
    ("vendor_series", "poweredge"): {"label": "PowerEdge", "label_kr": None},
    ("vendor_series", "proliant"): {"label": "ProLiant", "label_kr": None},
    ("vendor_series", "power"): {"label": "Power", "label_kr": None},
    ("vendor_series", "fas"): {"label": "FAS", "label_kr": None},
    ("vendor_series", "powerstore"): {"label": "PowerStore", "label_kr": None},
    ("vendor_series", "flasharray"): {"label": "FlashArray", "label_kr": None},
    ("vendor_series", "windows_server"): {"label": "Windows Server", "label_kr": None},
    ("vendor_series", "sql_server"): {"label": "SQL Server", "label_kr": None},
    ("vendor_series", "oracle_database"): {"label": "Oracle Database", "label_kr": None},
    ("vendor_series", "exadata"): {"label": "Exadata", "label_kr": None},
    ("vendor_series", "rhel"): {"label": "RHEL", "label_kr": None},
    ("vendor_series", "vsphere"): {"label": "vSphere", "label_kr": None},
    ("vendor_series", "splunk_enterprise"): {"label": "Splunk Enterprise", "label_kr": None},
    ("vendor_series", "falcon"): {"label": "Falcon", "label_kr": None},
    ("vendor_series", "openshift"): {"label": "OpenShift", "label_kr": None},
    ("vendor_series", "nginx_plus"): {"label": "NGINX Plus", "label_kr": None},

    # product_family
    ("product_family", "fw"): {"label": "Firewall", "label_kr": "방화벽"},
    ("product_family", "ips"): {"label": "IPS", "label_kr": None},
    ("product_family", "waf"): {"label": "WAF", "label_kr": None},
    ("product_family", "ddos"): {"label": "DDoS", "label_kr": None},
    ("product_family", "l2"): {"label": "L2 Switch", "label_kr": "L2 스위치"},
    ("product_family", "l3"): {"label": "L3 Switch", "label_kr": "L3 스위치"},
    ("product_family", "l4"): {"label": "L4 Switch", "label_kr": "L4 스위치"},
    ("product_family", "nms"): {"label": "NMS", "label_kr": None},
    ("product_family", "siem"): {"label": "SIEM", "label_kr": None},
    ("product_family", "prodtest"): {"label": "prodtest", "label_kr": None},
    ("product_family", "x86_server"): {"label": "x86 Server", "label_kr": "x86 서버"},
    ("product_family", "unix_server"): {"label": "UNIX Server", "label_kr": "UNIX 서버"},
    ("product_family", "nas"): {"label": "NAS", "label_kr": None},
    ("product_family", "san"): {"label": "SAN", "label_kr": None},
    ("product_family", "dbms"): {"label": "DBMS", "label_kr": None},
    ("product_family", "os"): {"label": "OS", "label_kr": None},
    ("product_family", "backup"): {"label": "Backup", "label_kr": "백업"},
    ("product_family", "middleware"): {"label": "Middleware", "label_kr": "미들웨어"},
    ("product_family", "generic"): {"label": "Generic", "label_kr": "기타"},
    ("product_family", "utm"): {"label": "UTM", "label_kr": None},
    ("product_family", "ids"): {"label": "IDS", "label_kr": None},
    ("product_family", "vpn"): {"label": "VPN", "label_kr": None},
    ("product_family", "router"): {"label": "Router", "label_kr": "라우터"},
    ("product_family", "switch"): {"label": "Switch", "label_kr": "스위치"},
    ("product_family", "adc"): {"label": "ADC", "label_kr": None},
    ("product_family", "load_balancer"): {"label": "Load Balancer", "label_kr": "로드밸런서"},
    ("product_family", "sdwan"): {"label": "SD-WAN", "label_kr": None},
    ("product_family", "dns"): {"label": "DNS", "label_kr": None},
    ("product_family", "dhcp_ipam"): {"label": "DHCP/IPAM", "label_kr": None},
    ("product_family", "monitoring"): {"label": "Monitoring", "label_kr": "모니터링"},
    ("product_family", "soar"): {"label": "SOAR", "label_kr": None},
    ("product_family", "dlp"): {"label": "DLP", "label_kr": None},
    ("product_family", "edr"): {"label": "EDR", "label_kr": None},
    ("product_family", "xdr"): {"label": "XDR", "label_kr": None},
    ("product_family", "iam"): {"label": "IAM", "label_kr": None},
    ("product_family", "pam"): {"label": "PAM", "label_kr": None},
    ("product_family", "pki"): {"label": "PKI", "label_kr": None},
    ("product_family", "proxy"): {"label": "Proxy", "label_kr": "프록시"},
    ("product_family", "mail_security"): {"label": "Mail Security", "label_kr": "메일 보안"},
    ("product_family", "ztna"): {"label": "ZTNA", "label_kr": None},
    ("product_family", "nac"): {"label": "NAC", "label_kr": None},
    ("product_family", "blade_server"): {"label": "Blade Server", "label_kr": "블레이드 서버"},
    ("product_family", "virtualization"): {"label": "Virtualization", "label_kr": "가상화"},
    ("product_family", "container_platform"): {"label": "Container Platform", "label_kr": "컨테이너 플랫폼"},
    ("product_family", "hci"): {"label": "HCI", "label_kr": None},
    ("product_family", "vdi"): {"label": "VDI", "label_kr": None},
    ("product_family", "object_storage"): {"label": "Object Storage", "label_kr": "오브젝트 스토리지"},
    ("product_family", "db_replication"): {"label": "DB Replication", "label_kr": "DB 복제"},
    ("product_family", "web_server"): {"label": "Web Server", "label_kr": "웹 서버"},
    ("product_family", "was"): {"label": "WAS", "label_kr": None},
    ("product_family", "backup_sw"): {"label": "Backup Software", "label_kr": "백업 소프트웨어"},
    ("product_family", "cache"): {"label": "Cache", "label_kr": "캐시"},
    ("product_family", "message_queue"): {"label": "Message Queue", "label_kr": "메시지 큐"},
    ("product_family", "etl"): {"label": "ETL", "label_kr": None},
    ("product_family", "batch_scheduler"): {"label": "Batch Scheduler", "label_kr": "배치 스케줄러"},
    ("product_family", "devops"): {"label": "DevOps Tools", "label_kr": "DevOps 도구"},
    ("product_family", "wlan_controller"): {"label": "WLAN Controller", "label_kr": "무선 컨트롤러"},
    ("product_family", "access_point"): {"label": "Access Point", "label_kr": "AP"},
    ("product_family", "optical"): {"label": "Optical Transport", "label_kr": "광전송장비"},
    ("product_family", "packet_broker"): {"label": "Packet Broker", "label_kr": "패킷 브로커"},
    ("product_family", "sandbox"): {"label": "Sandbox", "label_kr": "샌드박스"},
    ("product_family", "sase"): {"label": "SASE", "label_kr": None},
    ("product_family", "casb"): {"label": "CASB", "label_kr": None},
    ("product_family", "cspm"): {"label": "CSPM", "label_kr": None},
    ("product_family", "anti_malware"): {"label": "Anti-Malware", "label_kr": "안티멀웨어"},
    ("product_family", "threat_intel"): {"label": "Threat Intelligence", "label_kr": "위협 인텔리전스"},
    ("product_family", "db_access_control"): {"label": "DB Access Control", "label_kr": "DB 접근제어"},
    ("product_family", "swg"): {"label": "SWG", "label_kr": None},
    ("product_family", "sspm"): {"label": "SSPM", "label_kr": None},
    ("product_family", "gpu_server"): {"label": "GPU Server", "label_kr": "GPU 서버"},
    ("product_family", "hypervisor"): {"label": "Hypervisor", "label_kr": "하이퍼바이저"},
    ("product_family", "config_mgmt"): {"label": "Config Management", "label_kr": "형상관리"},
    ("product_family", "ci_cd"): {"label": "CI/CD", "label_kr": None},
    ("product_family", "log_mgmt"): {"label": "Log Management", "label_kr": "로그관리"},
    ("product_family", "automation"): {"label": "Automation Tools", "label_kr": "자동화 도구"},
    ("product_family", "api_gateway"): {"label": "API Gateway", "label_kr": "API 게이트웨이"},
    ("product_family", "tape"): {"label": "Tape", "label_kr": "테이프"},
    ("product_family", "sds"): {"label": "SDS", "label_kr": None},
    ("product_family", "cdp"): {"label": "CDP", "label_kr": None},
    ("product_family", "nosql"): {"label": "NoSQL", "label_kr": None},
    ("product_family", "data_warehouse"): {"label": "Data Warehouse", "label_kr": "데이터 웨어하우스"},
    ("product_family", "db_encryption"): {"label": "DB Encryption", "label_kr": "DB 암호화"},
    ("product_family", "in_memory_db"): {"label": "In-Memory DB", "label_kr": "인메모리 DB"},
}

# Entries whose DB label was Korean before this migration (upgrade changes them to English).
# Entries NOT in this set already had English labels — upgrade sets the same English value.
_LABELS_CHANGED_FROM_KOREAN: set[tuple[str, str]] = {
    # domain — all Korean
    ("domain", "net"), ("domain", "sec"), ("domain", "svr"),
    ("domain", "sto"), ("domain", "db"), ("domain", "app"),
    # imp_type — all Korean
    ("imp_type", "hw"), ("imp_type", "sw"), ("imp_type", "svc"),
    # license_model — only metered was Korean
    ("license_model", "metered"),
    # product_family — Korean originals
    ("product_family", "l2"), ("product_family", "l3"), ("product_family", "l4"),
    ("product_family", "x86_server"), ("product_family", "unix_server"),
    ("product_family", "backup"), ("product_family", "middleware"), ("product_family", "generic"),
    ("product_family", "router"), ("product_family", "switch"), ("product_family", "load_balancer"),
    ("product_family", "monitoring"), ("product_family", "proxy"), ("product_family", "mail_security"),
    ("product_family", "blade_server"), ("product_family", "virtualization"),
    ("product_family", "container_platform"), ("product_family", "object_storage"),
    ("product_family", "db_replication"), ("product_family", "web_server"),
    ("product_family", "backup_sw"), ("product_family", "cache"), ("product_family", "message_queue"),
    ("product_family", "batch_scheduler"), ("product_family", "devops"),
    ("product_family", "wlan_controller"), ("product_family", "access_point"),
    ("product_family", "optical"), ("product_family", "packet_broker"),
    ("product_family", "sandbox"), ("product_family", "anti_malware"),
    ("product_family", "threat_intel"), ("product_family", "db_access_control"),
    ("product_family", "gpu_server"), ("product_family", "hypervisor"),
    ("product_family", "config_mgmt"), ("product_family", "log_mgmt"),
    ("product_family", "automation"), ("product_family", "api_gateway"),
    ("product_family", "tape"), ("product_family", "data_warehouse"),
    ("product_family", "db_encryption"), ("product_family", "in_memory_db"),
}

# Downgrade reverse map: (attribute_key, option_key) -> original label before migration
ORIGINAL_LABELS: dict[tuple[str, str], str] = {}
for _key, _val in BACKFILL_MAP.items():
    if _key in _LABELS_CHANGED_FROM_KOREAN:
        # Original was Korean — restore to label_kr
        ORIGINAL_LABELS[_key] = _val["label_kr"]  # type: ignore[assignment]
    else:
        # Original was already English — restore to label
        ORIGINAL_LABELS[_key] = _val["label"]


def upgrade() -> None:
    conn = op.get_bind()

    # ── Step 1: Add label_kr column ──────────────────────────────
    op.add_column(
        "catalog_attribute_options",
        sa.Column("label_kr", sa.String(100), nullable=True),
    )

    # ── Step 2: Backfill label_kr and update label to English ────
    # Resolve attribute_key -> attribute id
    attrs = conn.execute(
        sa.text("SELECT id, attribute_key FROM catalog_attribute_defs")
    ).fetchall()
    attr_id_map = {row[1]: row[0] for row in attrs}

    updated_count = 0
    alias_count = 0
    now = _now()

    for (attr_key, opt_key), vals in BACKFILL_MAP.items():
        attr_id = attr_id_map.get(attr_key)
        if attr_id is None:
            print(f"  [SKIP] attribute '{attr_key}' not found")
            continue

        # Find the option row
        row = conn.execute(
            sa.text(
                "SELECT id FROM catalog_attribute_options "
                "WHERE attribute_id = :attr_id AND option_key = :opt_key"
            ),
            {"attr_id": attr_id, "opt_key": opt_key},
        ).fetchone()

        if row is None:
            print(f"  [SKIP] option '{attr_key}.{opt_key}' not found")
            continue

        option_id = row[0]

        # Update label (to English) and set label_kr
        conn.execute(
            sa.text(
                "UPDATE catalog_attribute_options "
                "SET label = :label, label_kr = :label_kr "
                "WHERE id = :id"
            ),
            {"label": vals["label"], "label_kr": vals["label_kr"], "id": option_id},
        )
        updated_count += 1

        # ── Step 3: Register label_kr as auto alias ──────────────
        if vals["label_kr"] is not None:
            normalized = _normalize_text(vals["label_kr"])
            if normalized:
                conn.execute(
                    sa.text(
                        "INSERT INTO catalog_attribute_option_aliases "
                        "(attribute_option_id, alias_value, normalized_alias, "
                        " match_type, sort_order, is_active, created_at, updated_at) "
                        "VALUES (:opt_id, :alias_val, :norm, "
                        " 'label_kr_auto', 0, true, :now, :now) "
                        "ON CONFLICT (attribute_option_id, normalized_alias) DO NOTHING"
                    ),
                    {
                        "opt_id": option_id,
                        "alias_val": vals["label_kr"],
                        "norm": normalized,
                        "now": now,
                    },
                )
                alias_count += 1

    print(f"  [0055] Updated {updated_count} options, inserted up to {alias_count} label_kr aliases")

    # ── Step 4: Verification ─────────────────────────────────────
    total = conn.execute(
        sa.text("SELECT count(*) FROM catalog_attribute_options WHERE label_kr IS NOT NULL")
    ).scalar()
    alias_total = conn.execute(
        sa.text(
            "SELECT count(*) FROM catalog_attribute_option_aliases "
            "WHERE match_type = 'label_kr_auto'"
        )
    ).scalar()
    print(f"  [0055] Verification: {total} options with label_kr, {alias_total} label_kr_auto aliases")


def downgrade() -> None:
    conn = op.get_bind()

    # ── Step 1: Remove label_kr_auto aliases ─────────────────────
    conn.execute(
        sa.text(
            "DELETE FROM catalog_attribute_option_aliases "
            "WHERE match_type = 'label_kr_auto'"
        )
    )

    # ── Step 2: Restore original labels ──────────────────────────
    attrs = conn.execute(
        sa.text("SELECT id, attribute_key FROM catalog_attribute_defs")
    ).fetchall()
    attr_id_map = {row[1]: row[0] for row in attrs}

    for (attr_key, opt_key), original_label in ORIGINAL_LABELS.items():
        attr_id = attr_id_map.get(attr_key)
        if attr_id is None:
            continue
        conn.execute(
            sa.text(
                "UPDATE catalog_attribute_options "
                "SET label = :label "
                "WHERE attribute_id = :attr_id AND option_key = :opt_key"
            ),
            {"label": original_label, "attr_id": attr_id, "opt_key": opt_key},
        )

    # ── Step 3: Drop label_kr column ─────────────────────────────
    op.drop_column("catalog_attribute_options", "label_kr")

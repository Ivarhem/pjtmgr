# -*- coding: utf-8 -*-
"""expand catalog seed data — attribute options, vendor aliases, products

Revision ID: 0054
Revises: 0053
Create Date: 2026-04-02
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "0054"
down_revision = "0053"
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
# 1. 신규 속성 옵션
# ─────────────────────────────────────────────

NEW_OPTIONS: dict[str, list[dict]] = {
    "domain": [
        {"option_key": "app", "label": "애플리케이션", "sort_order": 60},
    ],
    "platform": [
        {"option_key": "cloud", "label": "Cloud", "sort_order": 80},
        {"option_key": "virtual_appliance", "label": "Virtual Appliance", "sort_order": 90},
    ],
    "deployment_model": [
        {"option_key": "hybrid", "label": "Hybrid", "sort_order": 40},
        {"option_key": "paas", "label": "PaaS", "sort_order": 50},
    ],
    "license_model": [
        {"option_key": "open_source", "label": "Open Source", "sort_order": 50},
        {"option_key": "freemium", "label": "Freemium", "sort_order": 60},
        {"option_key": "metered", "label": "종량제", "sort_order": 70},
    ],
    "product_family": [
        # ── 네트워크 (net)
        {"option_key": "wlan_controller", "label": "무선 컨트롤러", "sort_order": 560},
        {"option_key": "access_point", "label": "AP", "sort_order": 570},
        {"option_key": "optical", "label": "광전송장비", "sort_order": 580},
        {"option_key": "packet_broker", "label": "패킷 브로커", "sort_order": 590},
        # ── 보안 (sec)
        {"option_key": "sandbox", "label": "샌드박스", "sort_order": 600},
        {"option_key": "sase", "label": "SASE", "sort_order": 610},
        {"option_key": "casb", "label": "CASB", "sort_order": 620},
        {"option_key": "cspm", "label": "CSPM", "sort_order": 630},
        {"option_key": "anti_malware", "label": "안티멀웨어", "sort_order": 640},
        {"option_key": "threat_intel", "label": "위협 인텔리전스", "sort_order": 650},
        {"option_key": "db_access_control", "label": "DB 접근제어", "sort_order": 660},
        {"option_key": "swg", "label": "SWG", "sort_order": 670},
        {"option_key": "sspm", "label": "SSPM", "sort_order": 680},
        # ── 서버 (svr)
        {"option_key": "gpu_server", "label": "GPU 서버", "sort_order": 690},
        {"option_key": "hypervisor", "label": "하이퍼바이저", "sort_order": 700},
        {"option_key": "config_mgmt", "label": "형상관리", "sort_order": 710},
        {"option_key": "ci_cd", "label": "CI/CD", "sort_order": 720},
        {"option_key": "log_mgmt", "label": "로그관리", "sort_order": 730},
        {"option_key": "automation", "label": "자동화 도구", "sort_order": 740},
        {"option_key": "api_gateway", "label": "API 게이트웨이", "sort_order": 750},
        # ── 스토리지 (sto)
        {"option_key": "tape", "label": "테이프", "sort_order": 760},
        {"option_key": "sds", "label": "SDS", "sort_order": 770},
        {"option_key": "cdp", "label": "CDP", "sort_order": 780},
        # ── 데이터베이스 (db)
        {"option_key": "nosql", "label": "NoSQL", "sort_order": 790},
        {"option_key": "data_warehouse", "label": "데이터 웨어하우스", "sort_order": 800},
        {"option_key": "db_encryption", "label": "DB 암호화", "sort_order": 810},
        {"option_key": "in_memory_db", "label": "인메모리 DB", "sort_order": 820},
    ],
}

# product_family 신규 옵션의 domain_scope 매핑
PRODUCT_FAMILY_DOMAIN_SCOPE: dict[str, str] = {
    "wlan_controller": "net",
    "access_point": "net",
    "optical": "net",
    "packet_broker": "net",
    "sandbox": "sec",
    "sase": "sec",
    "casb": "sec",
    "cspm": "sec",
    "anti_malware": "sec",
    "threat_intel": "sec",
    "db_access_control": "sec",
    "swg": "sec",
    "sspm": "sec",
    "gpu_server": "svr",
    "hypervisor": "svr",
    "config_mgmt": "svr",
    "ci_cd": "svr",
    "log_mgmt": "svr",
    "automation": "svr",
    "api_gateway": "svr",
    "tape": "sto",
    "sds": "sto",
    "cdp": "sto",
    "nosql": "db",
    "data_warehouse": "db",
    "db_encryption": "db",
    "in_memory_db": "db",
}


# ─────────────────────────────────────────────
# 2. 신규 벤더 별칭
# ─────────────────────────────────────────────

NEW_VENDOR_ALIASES: list[dict[str, str]] = [
    # 국산 벤더
    {"vendor_canonical": "SECUI", "alias_value": "시큐아이"},
    {"vendor_canonical": "AhnLab", "alias_value": "안랩"},
    {"vendor_canonical": "AhnLab", "alias_value": "Ahn Lab"},
    {"vendor_canonical": "Genians", "alias_value": "지니언스"},
    {"vendor_canonical": "WINS", "alias_value": "윈스"},
    {"vendor_canonical": "MONITORAPP", "alias_value": "모니터랩"},
    {"vendor_canonical": "IGLOO Security", "alias_value": "이글루시큐리티"},
    {"vendor_canonical": "IGLOO Security", "alias_value": "이글루"},
    {"vendor_canonical": "Samsung SDS", "alias_value": "삼성SDS"},
    {"vendor_canonical": "Samsung SDS", "alias_value": "삼성에스디에스"},
    {"vendor_canonical": "Hancom", "alias_value": "한컴"},
    {"vendor_canonical": "Hancom", "alias_value": "한글과컴퓨터"},
    {"vendor_canonical": "AXGATE", "alias_value": "엑스게이트"},
    {"vendor_canonical": "PENTA Security", "alias_value": "펜타시큐리티"},
    {"vendor_canonical": "PIOLINK", "alias_value": "파이오링크"},
    {"vendor_canonical": "PIOLINK", "alias_value": "Piolink"},
    # 해외 벤더 보강
    {"vendor_canonical": "Fortinet", "alias_value": "포티넷"},
    {"vendor_canonical": "VMware", "alias_value": "브이엠웨어"},
    {"vendor_canonical": "Microsoft", "alias_value": "MS"},
    {"vendor_canonical": "Microsoft", "alias_value": "마이크로소프트"},
    {"vendor_canonical": "Oracle", "alias_value": "오라클"},
    {"vendor_canonical": "Dell", "alias_value": "델"},
    {"vendor_canonical": "Check Point", "alias_value": "체크포인트"},
    {"vendor_canonical": "Check Point", "alias_value": "CheckPoint"},
    {"vendor_canonical": "SonicWall", "alias_value": "소닉월"},
    {"vendor_canonical": "Trend Micro", "alias_value": "트렌드마이크로"},
    {"vendor_canonical": "Trend Micro", "alias_value": "TrendMicro"},
    {"vendor_canonical": "Aruba", "alias_value": "아루바"},
    {"vendor_canonical": "Aruba", "alias_value": "Aruba Networks"},
    {"vendor_canonical": "Arista", "alias_value": "아리스타"},
    {"vendor_canonical": "Arista", "alias_value": "Arista Networks"},
    {"vendor_canonical": "Nutanix", "alias_value": "누타닉스"},
    {"vendor_canonical": "Citrix", "alias_value": "시트릭스"},
    {"vendor_canonical": "Veritas", "alias_value": "베리타스"},
    {"vendor_canonical": "Splunk", "alias_value": "스플렁크"},
    {"vendor_canonical": "MongoDB", "alias_value": "몽고DB"},
    {"vendor_canonical": "Elastic", "alias_value": "엘라스틱"},
    {"vendor_canonical": "HashiCorp", "alias_value": "하시코프"},
    {"vendor_canonical": "Broadcom", "alias_value": "브로드컴"},
]

# ─────────────────────────────────────────────
# 3. 신규 제품 시드 (~60개)
# ─────────────────────────────────────────────

NEW_PRODUCTS: list[dict[str, str | None]] = [
    # ── 네트워크 (net) ──
    {"vendor": "Cisco", "name": "Catalyst 9300", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "l3", "platform": "appliance"},
    {"vendor": "Cisco", "name": "Nexus 5000", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "l2", "platform": "appliance"},
    {"vendor": "Juniper", "name": "EX4400", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "l3", "platform": "appliance"},
    {"vendor": "Juniper", "name": "SRX4200", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "router", "platform": "appliance"},
    {"vendor": "Arista", "name": "7050X3", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "l3", "platform": "appliance"},
    {"vendor": "Aruba", "name": "CX 6300", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "l3", "platform": "appliance"},
    {"vendor": "Aruba", "name": "Mobility Controller 7200", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "wlan_controller", "platform": "appliance"},
    {"vendor": "Cisco", "name": "WLC 9800", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "wlan_controller", "platform": "appliance"},
    {"vendor": "Cisco", "name": "Catalyst 9120AXI", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "access_point", "platform": "appliance"},
    {"vendor": "PIOLINK", "name": "PAS-K 2424", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "adc", "platform": "appliance"},
    {"vendor": "Radware", "name": "Alteon VA", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "adc", "platform": "appliance"},
    {"vendor": "Gigamon", "name": "GigaVUE-HC3", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "packet_broker", "platform": "appliance"},
    {"vendor": "Nokia", "name": "7750 SR", "product_type": "hardware", "domain": "net", "imp_type": "hw", "product_family": "router", "platform": "appliance"},

    # ── 보안 (sec) ──
    {"vendor": "Check Point", "name": "Quantum 6200", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "fw", "platform": "appliance"},
    {"vendor": "SonicWall", "name": "NSa 4700", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "fw", "platform": "appliance"},
    {"vendor": "SECUI", "name": "BLUEMAX NGF 8000", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "fw", "platform": "appliance"},
    {"vendor": "AXGATE", "name": "NF 5000", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "fw", "platform": "appliance"},
    {"vendor": "AhnLab", "name": "TrusGuard 70B", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "fw", "platform": "appliance"},
    {"vendor": "WINS", "name": "SNIPER IPS 10000", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "ips", "platform": "appliance"},
    {"vendor": "MONITORAPP", "name": "AIWAF-500", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "waf", "platform": "appliance"},
    {"vendor": "PENTA Security", "name": "WAPPLES 2000", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "waf", "platform": "appliance"},
    {"vendor": "Genians", "name": "Genian NAC V5.0", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "nac", "platform": "linux"},
    {"vendor": "AhnLab", "name": "V3 Endpoint Security", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "anti_malware", "platform": "windows"},
    {"vendor": "Fortinet", "name": "FortiSandbox 3000F", "product_type": "hardware", "domain": "sec", "imp_type": "hw", "product_family": "sandbox", "platform": "appliance"},
    {"vendor": "IGLOO Security", "name": "SPiDER TM V5.x", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "siem", "platform": "linux"},
    {"vendor": "Zscaler", "name": "ZIA", "product_type": "service", "domain": "sec", "imp_type": "svc", "product_family": "sase", "platform": None},
    {"vendor": "Netskope", "name": "Cloud Security Platform", "product_type": "service", "domain": "sec", "imp_type": "svc", "product_family": "casb", "platform": None},
    {"vendor": "Fortinet", "name": "FortiEDR", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "edr", "platform": "linux"},
    {"vendor": "SentinelOne", "name": "Singularity XDR", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "xdr", "platform": "linux"},
    {"vendor": "Chakra Max", "name": "DB접근제어 V4", "product_type": "software", "domain": "sec", "imp_type": "sw", "product_family": "db_access_control", "platform": "linux"},

    # ── 서버 (svr) ──
    {"vendor": "HPE", "name": "ProLiant DL380 Gen11", "product_type": "hardware", "domain": "svr", "imp_type": "hw", "product_family": "x86_server", "platform": "x86"},
    {"vendor": "Lenovo", "name": "ThinkSystem SR650 V3", "product_type": "hardware", "domain": "svr", "imp_type": "hw", "product_family": "x86_server", "platform": "x86"},
    {"vendor": "Dell", "name": "PowerEdge R760xa", "product_type": "hardware", "domain": "svr", "imp_type": "hw", "product_family": "gpu_server", "platform": "x86"},
    {"vendor": "NVIDIA", "name": "DGX A100", "product_type": "hardware", "domain": "svr", "imp_type": "hw", "product_family": "gpu_server", "platform": "x86"},
    {"vendor": "Citrix", "name": "Hypervisor 8.2", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "hypervisor", "platform": "vm"},
    {"vendor": "Nutanix", "name": "AHV", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "hypervisor", "platform": "vm"},
    {"vendor": "Nutanix", "name": "HCI NX-8155-G8", "product_type": "hardware", "domain": "svr", "imp_type": "hw", "product_family": "hci", "platform": "x86"},
    {"vendor": "Kubernetes", "name": "Kubernetes 1.30", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "container_platform", "platform": "container"},
    {"vendor": "Ansible", "name": "Automation Platform 2", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "automation", "platform": "linux"},
    {"vendor": "HashiCorp", "name": "Terraform Enterprise", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "config_mgmt", "platform": "linux"},
    {"vendor": "GitLab", "name": "GitLab Ultimate", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "ci_cd", "platform": "linux"},
    {"vendor": "Jenkins", "name": "Jenkins LTS", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "ci_cd", "platform": "linux"},
    {"vendor": "Elastic", "name": "Elastic Stack 8", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "log_mgmt", "platform": "linux"},
    {"vendor": "Graylog", "name": "Graylog Enterprise", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "log_mgmt", "platform": "linux"},
    {"vendor": "Kong", "name": "Kong Gateway Enterprise", "product_type": "software", "domain": "svr", "imp_type": "sw", "product_family": "api_gateway", "platform": "linux"},

    # ── 스토리지 (sto) ──
    {"vendor": "NetApp", "name": "AFF A400", "product_type": "hardware", "domain": "sto", "imp_type": "hw", "product_family": "san", "platform": "appliance"},
    {"vendor": "HPE", "name": "Alletra 6070", "product_type": "hardware", "domain": "sto", "imp_type": "hw", "product_family": "san", "platform": "appliance"},
    {"vendor": "Synology", "name": "FlashStation FS2500", "product_type": "hardware", "domain": "sto", "imp_type": "hw", "product_family": "nas", "platform": "appliance"},
    {"vendor": "IBM", "name": "TS4300 Tape Library", "product_type": "hardware", "domain": "sto", "imp_type": "hw", "product_family": "tape", "platform": "appliance"},
    {"vendor": "Veritas", "name": "NetBackup 10.4", "product_type": "software", "domain": "sto", "imp_type": "sw", "product_family": "backup_sw", "platform": "linux"},
    {"vendor": "Ceph", "name": "Ceph Reef 18", "product_type": "software", "domain": "sto", "imp_type": "sw", "product_family": "sds", "platform": "linux"},

    # ── 데이터베이스 (db) ──
    {"vendor": "MongoDB", "name": "MongoDB Enterprise 7", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "nosql", "platform": "linux"},
    {"vendor": "Redis", "name": "Redis Enterprise 7", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "in_memory_db", "platform": "linux"},
    {"vendor": "MariaDB", "name": "MariaDB Enterprise Server 11", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "dbms", "platform": "linux"},
    {"vendor": "Tibero", "name": "Tibero 7", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "dbms", "platform": "linux"},
    {"vendor": "Snowflake", "name": "Snowflake Enterprise", "product_type": "service", "domain": "db", "imp_type": "svc", "product_family": "data_warehouse", "platform": None},
    {"vendor": "Cloudera", "name": "Cloudera Data Platform", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "data_warehouse", "platform": "linux"},
    {"vendor": "D'Amo", "name": "D'Amo KE", "product_type": "software", "domain": "db", "imp_type": "sw", "product_family": "db_encryption", "platform": "linux"},
]

# 신규 제품에서 등장하는 벤더 중 기존 alias 테이블에 없는 벤더 별칭
NEW_PRODUCT_VENDOR_ALIASES: list[dict[str, str]] = [
    {"vendor_canonical": "Lenovo", "alias_value": "레노버"},
    {"vendor_canonical": "NVIDIA", "alias_value": "엔비디아"},
    {"vendor_canonical": "Zscaler", "alias_value": "제트스케일러"},
    {"vendor_canonical": "SentinelOne", "alias_value": "센티넬원"},
    {"vendor_canonical": "Synology", "alias_value": "시놀로지"},
    {"vendor_canonical": "Radware", "alias_value": "래드웨어"},
    {"vendor_canonical": "Nokia", "alias_value": "노키아"},
    {"vendor_canonical": "Gigamon", "alias_value": "기가몬"},
    {"vendor_canonical": "Netskope", "alias_value": "넷스코프"},
    {"vendor_canonical": "D'Amo", "alias_value": "디아모"},
    {"vendor_canonical": "Tibero", "alias_value": "티베로"},
    {"vendor_canonical": "Tibero", "alias_value": "TmaxTibero"},
]


# ─────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────

def _attribute_id_map(conn) -> dict[str, int]:
    rows = conn.execute(
        sa.text("SELECT id, attribute_key FROM catalog_attribute_defs")
    ).mappings().all()
    return {row["attribute_key"]: int(row["id"]) for row in rows}


def _option_id_map(conn) -> dict[tuple[str, str], int]:
    rows = conn.execute(
        sa.text(
            "SELECT d.attribute_key, o.option_key, o.id "
            "FROM catalog_attribute_options o "
            "JOIN catalog_attribute_defs d ON d.id = o.attribute_id"
        )
    ).mappings().all()
    return {(row["attribute_key"], row["option_key"]): int(row["id"]) for row in rows}


def _product_exists(conn, vendor: str, name: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT 1 FROM product_catalog WHERE vendor = :vendor AND name = :name"),
            {"vendor": vendor, "name": name},
        ).scalar()
    )


def _vendor_alias_exists(conn, alias_value: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT 1 FROM catalog_vendor_aliases WHERE normalized_alias = :n"),
            {"n": _normalize_text(alias_value)},
        ).scalar()
    )


# ─────────────────────────────────────────────
# upgrade
# ─────────────────────────────────────────────

def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    # ── Step 1: 속성 옵션 upsert ──
    attr_ids = _attribute_id_map(conn)

    for attr_key, options in NEW_OPTIONS.items():
        attr_id = attr_ids.get(attr_key)
        if not attr_id:
            continue
        for opt in options:
            conn.execute(
                sa.text(
                    "INSERT INTO catalog_attribute_options "
                    "(attribute_id, option_key, label, sort_order, is_active, created_at, updated_at) "
                    "VALUES (:attribute_id, :option_key, :label, :sort_order, TRUE, :now, :now) "
                    "ON CONFLICT (attribute_id, option_key) DO NOTHING"
                ),
                {
                    "attribute_id": attr_id,
                    "option_key": opt["option_key"],
                    "label": opt["label"],
                    "sort_order": opt["sort_order"],
                    "now": now,
                },
            )

    # ── Step 2: product_family domain_scope 매핑 ──
    option_ids = _option_id_map(conn)
    for pf_key, domain_key in PRODUCT_FAMILY_DOMAIN_SCOPE.items():
        pf_tuple = ("product_family", pf_key)
        domain_tuple = ("domain", domain_key)
        pf_id = option_ids.get(pf_tuple)
        domain_id = option_ids.get(domain_tuple)
        if pf_id and domain_id:
            conn.execute(
                sa.text(
                    "UPDATE catalog_attribute_options "
                    "SET domain_option_id = :domain_id, updated_at = :now "
                    "WHERE id = :pf_id AND domain_option_id IS NULL"
                ),
                {"domain_id": domain_id, "pf_id": pf_id, "now": now},
            )

    # ── Step 3: 벤더 별칭 ──
    all_aliases = NEW_VENDOR_ALIASES + NEW_PRODUCT_VENDOR_ALIASES
    for alias in all_aliases:
        if _vendor_alias_exists(conn, alias["alias_value"]):
            continue
        conn.execute(
            sa.text(
                "INSERT INTO catalog_vendor_aliases "
                "(vendor_canonical, alias_value, normalized_alias, sort_order, is_active, created_at, updated_at) "
                "VALUES (:vendor_canonical, :alias_value, :normalized_alias, 100, TRUE, :now, :now)"
            ),
            {
                "vendor_canonical": alias["vendor_canonical"],
                "alias_value": alias["alias_value"],
                "normalized_alias": _normalize_text(alias["alias_value"]),
                "now": now,
            },
        )

    # ── Step 4: 제품 시드 ──
    # option_ids 갱신 (Step 1에서 새 옵션 추가했으므로)
    option_ids = _option_id_map(conn)
    attr_ids = _attribute_id_map(conn)

    for product in NEW_PRODUCTS:
        if _product_exists(conn, product["vendor"], product["name"]):
            continue

        product_id = conn.execute(
            sa.text(
                "INSERT INTO product_catalog "
                "(vendor, name, product_type, version, reference_url, "
                "normalized_vendor, normalized_name, is_placeholder, "
                "created_at, updated_at) "
                "VALUES (:vendor, :name, :product_type, :version, :reference_url, "
                ":normalized_vendor, :normalized_name, FALSE, :now, :now) "
                "RETURNING id"
            ),
            {
                "vendor": product["vendor"],
                "name": product["name"],
                "product_type": product["product_type"],
                "version": None,
                "reference_url": None,
                "normalized_vendor": _normalize_text(product["vendor"]),
                "normalized_name": _normalize_text(product["name"]),
                "now": now,
            },
        ).scalar_one()

        # 속성값 연결
        for attr_key in ("domain", "imp_type", "product_family", "platform"):
            opt_key = product.get(attr_key)
            if not opt_key:
                continue
            a_id = attr_ids.get(attr_key)
            o_id = option_ids.get((attr_key, opt_key))
            if not a_id or not o_id:
                continue
            conn.execute(
                sa.text(
                    "INSERT INTO product_catalog_attribute_values "
                    "(product_id, attribute_id, option_id, raw_value, "
                    "sort_order, is_primary, created_at, updated_at) "
                    "VALUES (:product_id, :attribute_id, :option_id, NULL, "
                    "100, TRUE, :now, :now)"
                ),
                {
                    "product_id": product_id,
                    "attribute_id": a_id,
                    "option_id": o_id,
                    "now": now,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()

    # 제품 삭제 (역순)
    for product in reversed(NEW_PRODUCTS):
        conn.execute(
            sa.text(
                "DELETE FROM product_catalog_attribute_values "
                "WHERE product_id IN ("
                "  SELECT id FROM product_catalog WHERE vendor = :vendor AND name = :name"
                ")"
            ),
            {"vendor": product["vendor"], "name": product["name"]},
        )
        conn.execute(
            sa.text("DELETE FROM product_catalog WHERE vendor = :vendor AND name = :name"),
            {"vendor": product["vendor"], "name": product["name"]},
        )

    # 벤더 별칭 삭제
    all_aliases = NEW_VENDOR_ALIASES + NEW_PRODUCT_VENDOR_ALIASES
    for alias in all_aliases:
        conn.execute(
            sa.text("DELETE FROM catalog_vendor_aliases WHERE normalized_alias = :n"),
            {"n": _normalize_text(alias["alias_value"])},
        )

    # product_family domain_scope 초기화
    for pf_key in PRODUCT_FAMILY_DOMAIN_SCOPE:
        conn.execute(
            sa.text(
                "UPDATE catalog_attribute_options SET domain_option_id = NULL "
                "WHERE option_key = :pf_key AND attribute_id IN ("
                "  SELECT id FROM catalog_attribute_defs WHERE attribute_key = 'product_family'"
                ")"
            ),
            {"pf_key": pf_key},
        )

    # 신규 옵션 삭제
    for attr_key, options in NEW_OPTIONS.items():
        for opt in options:
            conn.execute(
                sa.text(
                    "DELETE FROM catalog_attribute_options "
                    "WHERE option_key = :option_key AND attribute_id IN ("
                    "  SELECT id FROM catalog_attribute_defs WHERE attribute_key = :attr_key"
                    ")"
                ),
                {"option_key": opt["option_key"], "attr_key": attr_key},
            )

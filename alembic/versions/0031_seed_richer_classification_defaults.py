"""seed richer default classification nodes

Revision ID: 0031
Revises: 0030
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


_CHILDREN = {
    "HW-SRV": [
        ("HW-SRV-X86", "x86 서버", 10),
        ("HW-SRV-UNIX", "UNIX 서버", 20),
        ("HW-SRV-BLADE", "블레이드 서버", 30),
        ("HW-SRV-GPU", "GPU 서버", 40),
    ],
    "HW-STR": [
        ("HW-STR-SAN", "SAN 스토리지", 10),
        ("HW-STR-NAS", "NAS 스토리지", 20),
        ("HW-STR-BACKUP", "백업장비", 30),
    ],
    "HW-NET": [
        ("HW-NET-WAP", "무선AP", 60),
        ("HW-NET-CON", "콘솔서버", 70),
    ],
    "HW-SEC": [
        ("HW-SEC-WAF", "WAF", 50),
        ("HW-SEC-NAC", "NAC", 60),
        ("HW-SEC-UTM", "UTM", 70),
    ],
    "SW-OS": [
        ("SW-OS-LINUX", "Linux", 10),
        ("SW-OS-WIN", "Windows", 20),
        ("SW-OS-UNIX", "Unix", 30),
    ],
    "SW-DB": [
        ("SW-DB-ORA", "Oracle", 10),
        ("SW-DB-MSSQL", "MS SQL Server", 20),
        ("SW-DB-MYSQL", "MySQL/MariaDB", 30),
        ("SW-DB-PG", "PostgreSQL", 40),
    ],
    "SW-MW": [
        ("SW-MW-WEB", "WEB 서버", 10),
        ("SW-MW-WAS", "WAS", 20),
        ("SW-MW-MQ", "MQ", 30),
        ("SW-MW-TPM", "TP Monitor", 40),
    ],
    "SW-SEC": [
        ("SW-SEC-DBENC", "DB암호화", 10),
        ("SW-SEC-AC", "시스템접근제어", 20),
        ("SW-SEC-EDR", "EDR/백신", 30),
        ("SW-SEC-SIEM", "SIEM", 40),
    ],
    "SW-APP": [
        ("SW-APP-BIZ", "업무시스템", 10),
        ("SW-APP-OPS", "운영관리도구", 20),
        ("SW-APP-MON", "모니터링도구", 30),
        ("SW-APP-BACKUP", "백업소프트웨어", 40),
    ],
    "SVC-BIZ": [
        ("SVC-BIZ-ERP", "ERP", 10),
        ("SVC-BIZ-CRM", "CRM", 20),
        ("SVC-BIZ-GW", "그룹웨어", 30),
        ("SVC-BIZ-PORTAL", "포털", 40),
        ("SVC-BIZ-MES", "MES", 50),
    ],
    "SVC-COM": [
        ("SVC-COM-AUTH", "인증서비스", 10),
        ("SVC-COM-INTEG", "연동서비스", 20),
        ("SVC-COM-MSG", "메일/메시징", 30),
        ("SVC-COM-DEV", "개발플랫폼", 40),
    ],
    "SVC-DATA": [
        ("SVC-DATA-DW", "DW/DM", 10),
        ("SVC-DATA-ETL", "ETL/파이프라인", 20),
        ("SVC-DATA-LAKE", "데이터레이크", 30),
    ],
    "SVC-AI": [
        ("SVC-AI-LLM", "LLM", 10),
        ("SVC-AI-EMB", "임베딩모델", 20),
        ("SVC-AI-VIS", "비전모델", 30),
        ("SVC-AI-VOICE", "음성모델", 40),
    ],
}

_ALLOWED_MAPPING_SEEDS = [
    ("server", "HW-SRV-X86", False, True, 11, "x86 서버 허용 분류"),
    ("server", "HW-SRV-UNIX", False, True, 12, "UNIX 서버 허용 분류"),
    ("server", "HW-SRV-BLADE", False, True, 13, "블레이드 서버 허용 분류"),
    ("server", "HW-SRV-GPU", False, True, 14, "GPU 서버 허용 분류"),
    ("storage", "HW-STR-SAN", False, True, 21, "SAN 스토리지 허용 분류"),
    ("storage", "HW-STR-NAS", False, True, 22, "NAS 스토리지 허용 분류"),
    ("storage", "HW-STR-BACKUP", False, True, 23, "백업장비 허용 분류"),
    ("network", "HW-NET-WAP", False, True, 36, "무선AP 허용 분류"),
    ("network", "HW-NET-CON", False, True, 37, "콘솔서버 허용 분류"),
    ("security", "HW-SEC-WAF", False, True, 45, "WAF 허용 분류"),
    ("security", "HW-SEC-NAC", False, True, 46, "NAC 허용 분류"),
    ("security", "HW-SEC-UTM", False, True, 47, "UTM 허용 분류"),
    ("os", "SW-OS-LINUX", False, True, 111, "Linux 허용 분류"),
    ("os", "SW-OS-WIN", False, True, 112, "Windows 허용 분류"),
    ("os", "SW-OS-UNIX", False, True, 113, "Unix 허용 분류"),
    ("dbms", "SW-DB-ORA", False, True, 121, "Oracle 허용 분류"),
    ("dbms", "SW-DB-MSSQL", False, True, 122, "MS SQL Server 허용 분류"),
    ("dbms", "SW-DB-MYSQL", False, True, 123, "MySQL/MariaDB 허용 분류"),
    ("dbms", "SW-DB-PG", False, True, 124, "PostgreSQL 허용 분류"),
    ("middleware", "SW-MW-WEB", False, True, 131, "WEB 서버 허용 분류"),
    ("middleware", "SW-MW-WAS", False, True, 132, "WAS 허용 분류"),
    ("middleware", "SW-MW-MQ", False, True, 133, "MQ 허용 분류"),
    ("middleware", "SW-MW-TPM", False, True, 134, "TP Monitor 허용 분류"),
    ("application", "SW-APP-BIZ", False, True, 141, "업무시스템 허용 분류"),
    ("application", "SW-APP-OPS", False, True, 142, "운영관리도구 허용 분류"),
    ("application", "SW-APP-MON", False, True, 143, "모니터링도구 허용 분류"),
    ("application", "SW-APP-BACKUP", False, True, 144, "백업소프트웨어 허용 분류"),
    ("llm", "SVC-AI-LLM", False, True, 211, "LLM 허용 분류"),
    ("embedding_model", "SVC-AI-EMB", False, True, 221, "임베딩모델 허용 분류"),
    ("vision_model", "SVC-AI-VIS", False, True, 231, "비전모델 허용 분류"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("classification_nodes"):
        scheme_rows = bind.execute(
            sa.text("select id from classification_schemes where scope_type in ('global', 'project')")
        ).fetchall()
        for scheme_row in scheme_rows:
            scheme_id = scheme_row[0]
            node_rows = bind.execute(
                sa.text(
                    """
                    select id, node_code, level
                    from classification_nodes
                    where scheme_id = :scheme_id
                    """
                ),
                {"scheme_id": scheme_id},
            ).fetchall()
            node_map = {row._mapping["node_code"]: {"id": row._mapping["id"], "level": row._mapping["level"]} for row in node_rows}
            for parent_code, children in _CHILDREN.items():
                parent = node_map.get(parent_code)
                if not parent:
                    continue
                for child_code, child_name, sort_order in children:
                    if child_code in node_map:
                        continue
                    bind.execute(
                        sa.text(
                            """
                            insert into classification_nodes
                            (scheme_id, parent_id, node_code, node_name, level, sort_order, is_active, note, created_at, updated_at)
                            values
                            (:scheme_id, :parent_id, :node_code, :node_name, :level, :sort_order, true, null, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """
                        ),
                        {
                            "scheme_id": scheme_id,
                            "parent_id": parent["id"],
                            "node_code": child_code,
                            "node_name": child_name,
                            "level": parent["level"] + 1,
                            "sort_order": sort_order,
                        },
                    )

    if inspector.has_table("asset_type_classification_mappings"):
        existing_pairs = {
            (row._mapping["asset_type_key"], row._mapping["classification_node_code"])
            for row in bind.execute(
                sa.text(
                    "select asset_type_key, classification_node_code "
                    "from asset_type_classification_mappings"
                )
            ).fetchall()
        }
        for asset_type_key, node_code, is_default, is_allowed, sort_order, note in _ALLOWED_MAPPING_SEEDS:
            if (asset_type_key, node_code) in existing_pairs:
                continue
            bind.execute(
                sa.text(
                    """
                    insert into asset_type_classification_mappings
                    (asset_type_key, classification_node_code, is_default, is_allowed, sort_order, note, created_at, updated_at)
                    values
                    (:asset_type_key, :node_code, :is_default, :is_allowed, :sort_order, :note, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "asset_type_key": asset_type_key,
                    "node_code": node_code,
                    "is_default": is_default,
                    "is_allowed": is_allowed,
                    "sort_order": sort_order,
                    "note": note,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("asset_type_classification_mappings"):
        for asset_type_key, node_code, *_rest in _ALLOWED_MAPPING_SEEDS:
            bind.execute(
                sa.text(
                    """
                    delete from asset_type_classification_mappings
                    where asset_type_key = :asset_type_key
                      and classification_node_code = :node_code
                    """
                ),
                {"asset_type_key": asset_type_key, "node_code": node_code},
            )

    if inspector.has_table("classification_nodes"):
        child_codes = [child_code for children in _CHILDREN.values() for child_code, _name, _order in children]
        for child_code in child_codes:
            bind.execute(
                sa.text("delete from classification_nodes where node_code = :node_code"),
                {"node_code": child_code},
            )

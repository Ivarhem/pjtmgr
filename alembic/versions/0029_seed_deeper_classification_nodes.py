"""seed deeper default classification nodes

Revision ID: 0029
Revises: 0028
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


_CHILDREN = {
    "HW-NET": [
        ("HW-NET-RT", "라우터", 10),
        ("HW-NET-L2", "L2 스위치", 20),
        ("HW-NET-L3", "L3 스위치", 30),
        ("HW-NET-L4", "L4 스위치", 40),
        ("HW-NET-PBR", "패킷브로커", 50),
    ],
    "HW-SEC": [
        ("HW-SEC-FW", "방화벽", 10),
        ("HW-SEC-VPN", "VPN", 20),
        ("HW-SEC-IPS", "IPS", 30),
        ("HW-SEC-DDOS", "DDoS", 40),
    ],
}

_ALLOWED_MAPPING_SEEDS = [
    ("network", "HW-NET-RT", False, True, 31, "라우터 허용 분류"),
    ("network", "HW-NET-L2", False, True, 32, "L2 스위치 허용 분류"),
    ("network", "HW-NET-L3", False, True, 33, "L3 스위치 허용 분류"),
    ("network", "HW-NET-L4", False, True, 34, "L4 스위치 허용 분류"),
    ("network", "HW-NET-PBR", False, True, 35, "패킷브로커 허용 분류"),
    ("security", "HW-SEC-FW", False, True, 41, "방화벽 허용 분류"),
    ("security", "HW-SEC-VPN", False, True, 42, "VPN 허용 분류"),
    ("security", "HW-SEC-IPS", False, True, 43, "IPS 허용 분류"),
    ("security", "HW-SEC-DDOS", False, True, 44, "DDoS 허용 분류"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("classification_nodes"):
        return

    schemes = bind.execute(
        sa.text("select id from classification_schemes where scope_type in ('global', 'project')")
    ).fetchall()
    for (scheme_id,) in schemes:
        rows = bind.execute(
            sa.text(
                """
                select id, node_code, level
                from classification_nodes
                where scheme_id = :scheme_id
                """
            ),
            {"scheme_id": scheme_id},
        ).fetchall()
        node_map = {row.node_code: {"id": row.id, "level": row.level} for row in rows}
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
            (row[0], row[1])
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

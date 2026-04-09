"""seed default asset type classification mappings

Revision ID: 0028
Revises: 0027
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


_DEFAULT_MAPPINGS = [
    ("server", "HW-SRV", True, True, 10, "기본 서버 분류"),
    ("storage", "HW-STR", True, True, 20, "기본 스토리지 분류"),
    ("network", "HW-NET", True, True, 30, "기본 네트워크 분류"),
    ("security", "HW-SEC", True, True, 40, "기본 보안장비 분류"),
    ("other", "HW-ETC", True, True, 90, "기타 하드웨어 분류"),
    ("os", "SW-OS", True, True, 110, "기본 운영체제 분류"),
    ("dbms", "SW-DB", True, True, 120, "기본 DBMS 분류"),
    ("middleware", "SW-MW", True, True, 130, "기본 미들웨어 분류"),
    ("application", "SW-APP", True, True, 140, "기본 애플리케이션 분류"),
    ("llm", "SVC-AI", True, True, 210, "기본 LLM 분류"),
    ("embedding_model", "SVC-AI", True, True, 220, "기본 임베딩 모델 분류"),
    ("vision_model", "SVC-AI", True, True, 230, "기본 비전 모델 분류"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("asset_type_classification_mappings"):
        return

    existing_pairs = {
        (row[0], row[1])
        for row in bind.execute(
            sa.text(
                "select asset_type_key, classification_node_code "
                "from asset_type_classification_mappings"
            )
        ).fetchall()
    }
    existing_asset_types = {
        row[0] for row in bind.execute(sa.text("select type_key from asset_type_codes")).fetchall()
    }
    existing_node_codes = {
        row[0]
        for row in bind.execute(
            sa.text(
                "select n.node_code "
                "from classification_nodes n "
                "join classification_schemes s on s.id = n.scheme_id "
                "where s.scope_type = 'global'"
            )
        ).fetchall()
    }

    for asset_type_key, node_code, is_default, is_allowed, sort_order, note in _DEFAULT_MAPPINGS:
        if asset_type_key not in existing_asset_types or node_code not in existing_node_codes:
            continue
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
    if not inspector.has_table("asset_type_classification_mappings"):
        return
    for asset_type_key, node_code, *_rest in _DEFAULT_MAPPINGS:
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

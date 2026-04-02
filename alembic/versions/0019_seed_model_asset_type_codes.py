"""Seed additional software/model asset type codes.

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"


_ROWS = [
    {"type_key": "os", "code": "OSW", "label": "운영체제", "kind": "software", "sort_order": 5},
    {"type_key": "dbms", "code": "DBM", "label": "DBMS", "kind": "software", "sort_order": 6},
    {"type_key": "llm", "code": "LLM", "label": "LLM", "kind": "model", "sort_order": 9},
    {"type_key": "embedding_model", "code": "EMB", "label": "임베딩모델", "kind": "model", "sort_order": 10},
    {"type_key": "vision_model", "code": "VIS", "label": "비전모델", "kind": "model", "sort_order": 11},
]


def upgrade() -> None:
    conn = op.get_bind()
    for row in _ROWS:
        exists = conn.execute(
            sa.text("SELECT 1 FROM asset_type_codes WHERE type_key = :type_key"),
            {"type_key": row["type_key"]},
        ).scalar()
        if exists:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO asset_type_codes (type_key, code, label, kind, sort_order, is_active) "
                "VALUES (:type_key, :code, :label, :kind, :sort_order, true)"
            ),
            row,
        )


def downgrade() -> None:
    conn = op.get_bind()
    for type_key in ("vision_model", "embedding_model", "llm", "dbms", "os"):
        conn.execute(
            sa.text("DELETE FROM asset_type_codes WHERE type_key = :type_key"),
            {"type_key": type_key},
        )

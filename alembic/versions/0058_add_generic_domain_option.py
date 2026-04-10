"""add generic domain option and map product_family generic to it

Revision ID: 0058
Revises: 91fa5696df75
Create Date: 2026-04-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0058"
down_revision: str = "91fa5696df75"
branch_labels = None
depends_on = None


def _attribute_id(conn, attribute_key: str) -> int | None:
    return conn.execute(
        sa.text("SELECT id FROM catalog_attribute_defs WHERE attribute_key = :k"),
        {"k": attribute_key},
    ).scalar()


def _option_id(conn, attribute_id: int, option_key: str) -> int | None:
    return conn.execute(
        sa.text(
            "SELECT id FROM catalog_attribute_options "
            "WHERE attribute_id = :aid AND option_key = :ok"
        ),
        {"aid": attribute_id, "ok": option_key},
    ).scalar()


def upgrade() -> None:
    conn = op.get_bind()
    domain_attr_id = _attribute_id(conn, "domain")
    if domain_attr_id is None:
        return

    # domain에 generic 옵션이 없으면 추가
    generic_domain_id = _option_id(conn, domain_attr_id, "generic")
    if generic_domain_id is None:
        # 기존 최대 sort_order 뒤에 배치
        max_sort = conn.execute(
            sa.text(
                "SELECT COALESCE(MAX(sort_order), 0) "
                "FROM catalog_attribute_options WHERE attribute_id = :aid"
            ),
            {"aid": domain_attr_id},
        ).scalar()
        conn.execute(
            sa.text(
                "INSERT INTO catalog_attribute_options "
                "(attribute_id, option_key, label, label_kr, sort_order, is_active, created_at, updated_at) "
                "VALUES (:aid, 'generic', 'Generic', '기타', :so, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"aid": domain_attr_id, "so": (max_sort or 0) + 10},
        )
        generic_domain_id = _option_id(conn, domain_attr_id, "generic")

    # product_family generic → domain generic 매핑
    pf_attr_id = _attribute_id(conn, "product_family")
    if pf_attr_id is None or generic_domain_id is None:
        return
    pf_generic_id = _option_id(conn, pf_attr_id, "generic")
    if pf_generic_id is None:
        return
    conn.execute(
        sa.text(
            "UPDATE catalog_attribute_options "
            "SET domain_option_id = :did "
            "WHERE id = :pid AND attribute_id = :aid"
        ),
        {"did": generic_domain_id, "pid": pf_generic_id, "aid": pf_attr_id},
    )


def downgrade() -> None:
    conn = op.get_bind()
    # product_family generic의 domain_option_id 해제
    pf_attr_id = _attribute_id(conn, "product_family")
    if pf_attr_id:
        pf_generic_id = _option_id(conn, pf_attr_id, "generic")
        if pf_generic_id:
            conn.execute(
                sa.text(
                    "UPDATE catalog_attribute_options "
                    "SET domain_option_id = NULL "
                    "WHERE id = :pid"
                ),
                {"pid": pf_generic_id},
            )
    # domain generic 옵션 삭제
    domain_attr_id = _attribute_id(conn, "domain")
    if domain_attr_id:
        conn.execute(
            sa.text(
                "DELETE FROM catalog_attribute_options "
                "WHERE attribute_id = :aid AND option_key = 'generic'"
            ),
            {"aid": domain_attr_id},
        )

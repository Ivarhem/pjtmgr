# -*- coding: utf-8 -*-
"""Normalize catalog layouts to one key per depth.

Revision ID: 0041
Revises: 0040
Create Date: 2026-03-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def _fetch_id(conn, sql: str, **params) -> int | None:
    row = conn.execute(sa.text(sql), params).fetchone()
    return None if row is None else int(row[0])


def _attribute_id(conn, attribute_key: str) -> int | None:
    return _fetch_id(
        conn,
        "SELECT id FROM catalog_attribute_defs WHERE attribute_key = :attribute_key",
        attribute_key=attribute_key,
    )


def _layout_id(conn, name: str) -> int | None:
    return _fetch_id(
        conn,
        "SELECT id FROM classification_layouts WHERE scope_type = 'global' AND name = :name",
        name=name,
    )


def _level_id(conn, layout_id: int, level_no: int) -> int | None:
    return _fetch_id(
        conn,
        "SELECT id FROM classification_layout_levels WHERE layout_id = :layout_id AND level_no = :level_no",
        layout_id=layout_id,
        level_no=level_no,
    )


def _ensure_level(conn, layout_id: int, level_no: int, alias: str, sort_order: int) -> int:
    level_id = _level_id(conn, layout_id, level_no)
    if level_id is not None:
        conn.execute(
            sa.text(
                """
                UPDATE classification_layout_levels
                SET alias = :alias,
                    joiner = ', ',
                    prefix_mode = NULL,
                    sort_order = :sort_order
                WHERE id = :level_id
                """
            ),
            {"level_id": level_id, "alias": alias, "sort_order": sort_order},
        )
        return level_id
    row = conn.execute(
        sa.text(
            """
            INSERT INTO classification_layout_levels (
                layout_id, level_no, alias, joiner, prefix_mode, sort_order, created_at, updated_at
            ) VALUES (
                :layout_id, :level_no, :alias, ', ', NULL, :sort_order, NOW(), NOW()
            )
            RETURNING id
            """
        ),
        {"layout_id": layout_id, "level_no": level_no, "alias": alias, "sort_order": sort_order},
    ).fetchone()
    return int(row[0])


def _replace_level_key(conn, level_id: int, attribute_id: int) -> None:
    conn.execute(
        sa.text("DELETE FROM classification_layout_level_keys WHERE level_id = :level_id"),
        {"level_id": level_id},
    )
    conn.execute(
        sa.text(
            """
            INSERT INTO classification_layout_level_keys (
                level_id, attribute_id, sort_order, is_visible, created_at, updated_at
            ) VALUES (
                :level_id, :attribute_id, 100, TRUE, NOW(), NOW()
            )
            """
        ),
        {"level_id": level_id, "attribute_id": attribute_id},
    )


def _normalize_layout(conn, name: str, level_plan: list[tuple[int, str, str]]) -> None:
    layout_id = _layout_id(conn, name)
    if layout_id is None:
        return
    conn.execute(
        sa.text(
            """
            UPDATE classification_layouts
            SET depth_count = :depth_count,
                description = :description,
                updated_at = NOW()
            WHERE id = :layout_id
            """
        ),
        {
            "layout_id": layout_id,
            "depth_count": len(level_plan),
            "description": " > ".join(alias for _, alias, _ in level_plan),
        },
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM classification_layout_level_keys
            WHERE level_id IN (
                SELECT id FROM classification_layout_levels
                WHERE layout_id = :layout_id
                  AND level_no > :depth_count
            )
            """
        ),
        {"layout_id": layout_id, "depth_count": len(level_plan)},
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM classification_layout_levels
            WHERE layout_id = :layout_id
              AND level_no > :depth_count
            """
        ),
        {"layout_id": layout_id, "depth_count": len(level_plan)},
    )
    for level_no, alias, attribute_key in level_plan:
        level_id = _ensure_level(conn, layout_id, level_no, alias, level_no * 10)
        attribute_id = _attribute_id(conn, attribute_key)
        if attribute_id is not None:
            _replace_level_key(conn, level_id, attribute_id)


def upgrade() -> None:
    conn = op.get_bind()
    _normalize_layout(
        conn,
        "기술기준형",
        [
            (1, "대분류", "domain"),
            (2, "중분류", "imp_type"),
            (3, "소분류", "product_family"),
            (4, "세구분", "platform"),
        ],
    )
    _normalize_layout(
        conn,
        "제품군우선형",
        [
            (1, "대분류", "domain"),
            (2, "중분류", "product_family"),
            (3, "소분류", "imp_type"),
            (4, "세구분", "platform"),
        ],
    )


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")

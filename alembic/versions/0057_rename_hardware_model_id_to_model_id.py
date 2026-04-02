# -*- coding: utf-8 -*-
"""Rename hardware_model_id to model_id, make NOT NULL, change ondelete to RESTRICT.

Revision ID: 0057
Revises: 0056
Create Date: 2026-04-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. NULL인 자산 삭제 (연관 테이블 포함)
    op.execute("""
        DELETE FROM period_assets WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_aliases WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_events WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_role_assignments WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_contacts WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_relations WHERE src_asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        ) OR dst_asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_related_partners WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_ips WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_software WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM policy_assignments WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM port_maps WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("DELETE FROM assets WHERE hardware_model_id IS NULL")

    # 2. 기존 FK 제약 삭제
    op.drop_constraint("assets_hardware_model_id_fkey", "assets", type_="foreignkey")
    op.drop_index("ix_assets_hardware_model_id", "assets")

    # 3. 컬럼 리네임
    op.alter_column("assets", "hardware_model_id", new_column_name="model_id")

    # 4. NOT NULL 설정
    op.alter_column("assets", "model_id", nullable=False)

    # 5. 새 FK (RESTRICT) + 인덱스
    op.create_foreign_key(
        "assets_model_id_fkey", "assets",
        "product_catalog", ["model_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_assets_model_id", "assets", ["model_id"])


def downgrade() -> None:
    op.drop_constraint("assets_model_id_fkey", "assets", type_="foreignkey")
    op.drop_index("ix_assets_model_id", "assets")
    op.alter_column("assets", "model_id", new_column_name="hardware_model_id")
    op.alter_column("assets", "hardware_model_id", nullable=True)
    op.create_foreign_key(
        "assets_hardware_model_id_fkey", "assets",
        "product_catalog", ["hardware_model_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_assets_hardware_model_id", "assets", ["hardware_model_id"])

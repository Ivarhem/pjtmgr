# -*- coding: utf-8 -*-
"""drop asset identity rules

Revision ID: 0046
Revises: 0045
Create Date: 2026-03-30
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "asset_identity_rules" not in inspector.get_table_names():
        return
    for index_name in (
        "ix_asset_identity_rules_priority",
        "ix_asset_identity_rules_platform_option_id",
        "ix_asset_identity_rules_product_family_option_id",
        "ix_asset_identity_rules_imp_type_option_id",
        "ix_asset_identity_rules_domain_option_id",
    ):
        existing_indexes = {item["name"] for item in inspector.get_indexes("asset_identity_rules")}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="asset_identity_rules")
    op.drop_table("asset_identity_rules")


def downgrade() -> None:
    raise NotImplementedError("Irreversible migration")

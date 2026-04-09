"""add default_license_type and default_license_unit to product_catalog

Revision ID: 119c27c908e8
Revises: 88dbdbf22921
Create Date: 2026-04-09 10:15:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '119c27c908e8'
down_revision: Union[str, None] = '88dbdbf22921'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('product_catalog', sa.Column('default_license_type', sa.String(length=50), nullable=True))
    op.add_column('product_catalog', sa.Column('default_license_unit', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('product_catalog', 'default_license_unit')
    op.drop_column('product_catalog', 'default_license_type')

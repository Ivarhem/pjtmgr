"""split licensed_to into license_unit and license_quantity

Revision ID: 88dbdbf22921
Revises: 0069
Create Date: 2026-04-09 09:34:47.144382
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '88dbdbf22921'
down_revision: Union[str, None] = '0069'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('asset_licenses', sa.Column('license_unit', sa.String(length=50), nullable=True))
    op.add_column('asset_licenses', sa.Column('license_quantity', sa.String(length=100), nullable=True))
    op.drop_column('asset_licenses', 'licensed_to')


def downgrade() -> None:
    op.add_column('asset_licenses', sa.Column('licensed_to', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
    op.drop_column('asset_licenses', 'license_quantity')
    op.drop_column('asset_licenses', 'license_unit')

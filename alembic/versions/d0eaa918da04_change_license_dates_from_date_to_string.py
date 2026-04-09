"""change license dates from date to string

Revision ID: d0eaa918da04
Revises: 119c27c908e8
Create Date: 2026-04-09 10:10:26.436133
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd0eaa918da04'
down_revision: Union[str, None] = '119c27c908e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('asset_licenses', 'start_date',
               existing_type=sa.Date(),
               type_=sa.String(length=50),
               existing_nullable=True)
    op.alter_column('asset_licenses', 'end_date',
               existing_type=sa.Date(),
               type_=sa.String(length=50),
               existing_nullable=True)


def downgrade() -> None:
    op.alter_column('asset_licenses', 'end_date',
               existing_type=sa.String(length=50),
               type_=sa.Date(),
               existing_nullable=True,
               postgresql_using='end_date::date')
    op.alter_column('asset_licenses', 'start_date',
               existing_type=sa.String(length=50),
               type_=sa.Date(),
               existing_nullable=True,
               postgresql_using='start_date::date')

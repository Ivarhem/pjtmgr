"""add catalog_vendor_meta table

Revision ID: 91fa5696df75
Revises: 0057
Create Date: 2026-04-03 14:09:20.103046
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '91fa5696df75'
down_revision: Union[str, None] = '0057'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'catalog_vendor_meta',
        sa.Column('vendor_canonical', sa.String(100), primary_key=True, comment='대표 제조사명 (영문)'),
        sa.Column('name_ko', sa.String(100), nullable=True, comment='제조사명 (한글)'),
        sa.Column('memo', sa.Text(), nullable=True, comment='메모'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('catalog_vendor_meta')

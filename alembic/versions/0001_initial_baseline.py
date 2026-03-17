"""initial baseline - 기존 스키마 스탬프

Revision ID: 0001
Revises:
Create Date: 2026-03-16
"""
from __future__ import annotations

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 기존 테이블이 이미 존재하므로 변경 없음 (baseline stamp)
    pass


def downgrade() -> None:
    raise RuntimeError("baseline 이전으로 downgrade할 수 없습니다.")

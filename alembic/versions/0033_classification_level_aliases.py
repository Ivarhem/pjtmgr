"""add classification level aliases

Revision ID: 0033
Revises: 0032
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("classification_schemes", sa.Column("level_1_alias", sa.String(length=40), nullable=True))
    op.add_column("classification_schemes", sa.Column("level_2_alias", sa.String(length=40), nullable=True))
    op.add_column("classification_schemes", sa.Column("level_3_alias", sa.String(length=40), nullable=True))
    op.add_column("classification_schemes", sa.Column("level_4_alias", sa.String(length=40), nullable=True))
    op.add_column("classification_schemes", sa.Column("level_5_alias", sa.String(length=40), nullable=True))

    conn = op.get_bind()
    schemes = sa.table(
        "classification_schemes",
        sa.column("id", sa.Integer),
        sa.column("level_1_alias", sa.String),
        sa.column("level_2_alias", sa.String),
        sa.column("level_3_alias", sa.String),
        sa.column("level_4_alias", sa.String),
        sa.column("level_5_alias", sa.String),
    )
    conn.execute(
        sa.update(schemes).values(
            level_1_alias="대구분",
            level_2_alias="중구분",
            level_3_alias="소구분",
            level_4_alias="세구분",
            level_5_alias="상세구분",
        )
    )


def downgrade() -> None:
    op.drop_column("classification_schemes", "level_5_alias")
    op.drop_column("classification_schemes", "level_4_alias")
    op.drop_column("classification_schemes", "level_3_alias")
    op.drop_column("classification_schemes", "level_2_alias")
    op.drop_column("classification_schemes", "level_1_alias")

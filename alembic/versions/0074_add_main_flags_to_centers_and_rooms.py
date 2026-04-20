"""add main flags to centers and rooms

Revision ID: 0074
Revises: 0073
Create Date: 2026-04-20 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0074"
down_revision = "0073"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("centers", sa.Column("is_main", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("rooms", sa.Column("is_main", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.execute(
        """
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY partner_id ORDER BY id) AS rn
            FROM centers
        )
        UPDATE centers c
        SET is_main = CASE WHEN ranked.rn = 1 THEN true ELSE false END
        FROM ranked
        WHERE ranked.id = c.id
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY center_id ORDER BY id) AS rn
            FROM rooms
        )
        UPDATE rooms r
        SET is_main = CASE WHEN ranked.rn = 1 THEN true ELSE false END
        FROM ranked
        WHERE ranked.id = r.id
        """
    )

    op.alter_column("centers", "is_main", server_default=None)
    op.alter_column("rooms", "is_main", server_default=None)


def downgrade() -> None:
    op.drop_column("rooms", "is_main")
    op.drop_column("centers", "is_main")

"""product similarity dismissal table

Revision ID: 0059
Revises: 0058
"""
from alembic import op
import sqlalchemy as sa

revision = "0059"
down_revision = "0058"


def upgrade() -> None:
    op.create_table(
        "product_similarity_dismissal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id_a", sa.Integer(), sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id_b", sa.Integer(), sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("product_id_a", "product_id_b", name="uq_similarity_dismissal_pair"),
    )


def downgrade() -> None:
    op.drop_table("product_similarity_dismissal")

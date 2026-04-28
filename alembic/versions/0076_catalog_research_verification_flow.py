"""catalog research verification flow

Revision ID: 0076
Revises: 0075
Create Date: 2026-04-23 13:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0076"
down_revision = "0075"
branch_labels = None
depends_on = None


STATUS_MAP_SQL = """
UPDATE product_catalog
SET verification_status = CASE
    WHEN lower(coalesce(verification_status, '')) IN ('review_needed', 'pending_review') THEN 'pending_review'
    WHEN lower(coalesce(verification_status, '')) IN ('verified', 'completed', 'reviewed', 'manual', 'imported') THEN 'verified'
    WHEN coalesce(trim(verification_status), '') = '' THEN 'unverified'
    ELSE lower(verification_status)
END
"""


def upgrade() -> None:
    op.add_column("product_catalog", sa.Column("researched_at", sa.DateTime(), nullable=True))
    op.add_column("product_catalog", sa.Column("research_provider", sa.String(length=30), nullable=True))

    op.execute(STATUS_MAP_SQL)
    op.execute(
        """
        UPDATE product_catalog
        SET researched_at = COALESCE(researched_at, last_verified_at)
        WHERE lower(coalesce(source_name, '')) = 'catalog_research'
        """
    )
    op.execute(
        """
        UPDATE product_catalog
        SET last_verified_at = NULL
        WHERE lower(coalesce(source_name, '')) = 'catalog_research'
          AND verification_status = 'pending_review'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE product_catalog
        SET verification_status = CASE
            WHEN verification_status = 'pending_review' THEN 'review_needed'
            WHEN verification_status = 'unverified' THEN NULL
            ELSE verification_status
        END
        """
    )
    op.drop_column("product_catalog", "research_provider")
    op.drop_column("product_catalog", "researched_at")

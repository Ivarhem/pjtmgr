"""backfill product catalog family fields

Revision ID: 0078
Revises: 0077
Create Date: 2026-04-24 16:18:00
"""

from alembic import op


revision = "0078"
down_revision = "0077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE product_catalog
        SET model_family = upper(substring(name from '^([A-Za-z]+[0-9]+[A-Za-z]*)-')),
            is_family_level = false
        WHERE product_type = 'hardware'
          AND lower(vendor) = 'cisco'
          AND (model_family IS NULL OR model_family = '')
          AND name ~ '^[A-Za-z]+[0-9]+[A-Za-z]*-[A-Za-z0-9]';
        """
    )

    op.execute(
        """
        UPDATE product_catalog
        SET model_family = upper(name),
            is_family_level = true
        WHERE product_type = 'hardware'
          AND lower(vendor) = 'cisco'
          AND (model_family IS NULL OR model_family = '')
          AND name ~ '^[A-Za-z]+[0-9]+[A-Za-z]*$';
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE product_catalog
        SET model_family = NULL,
            is_family_level = false
        WHERE product_type = 'hardware'
          AND lower(vendor) = 'cisco';
        """
    )

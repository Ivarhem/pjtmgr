"""expand hardware sku families

Revision ID: 0079
Revises: 0078
Create Date: 2026-04-28 12:35:00
"""

from alembic import op


revision = "0079"
down_revision = "0078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    updates = [
        ("cisco", "Catalyst 9300", "C9300"),
        ("juniper", "EX4400", "EX4400"),
        ("arista", "7050X3", "7050X3"),
        ("aruba", "CX 6300", "CX 6300"),
    ]
    for vendor, name, family in updates:
        op.execute(
            f"""
            UPDATE product_catalog
            SET model_family = '{family}', is_family_level = true
            WHERE product_type = 'hardware'
              AND lower(vendor) = '{vendor}'
              AND name = '{name}';
            """
        )


def downgrade() -> None:
    op.execute(
        """
        UPDATE product_catalog
        SET model_family = NULL, is_family_level = false
        WHERE product_type = 'hardware'
          AND (
            (lower(vendor) = 'cisco' AND name = 'Catalyst 9300') OR
            (lower(vendor) = 'juniper' AND name = 'EX4400') OR
            (lower(vendor) = 'arista' AND name = '7050X3') OR
            (lower(vendor) = 'aruba' AND name = 'CX 6300')
          );
        """
    )

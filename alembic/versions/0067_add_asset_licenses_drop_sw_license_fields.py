"""Add asset_licenses table, drop license_type/license_count from asset_software.

Revision ID: 0067
Revises: 0066
"""
from alembic import op
import sqlalchemy as sa

revision = "0067"
down_revision = "0066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL with IF NOT EXISTS to handle pre-existing table
    op.execute("""
        CREATE TABLE IF NOT EXISTS asset_licenses (
            id SERIAL NOT NULL,
            asset_id INTEGER NOT NULL,
            license_type VARCHAR(50) NOT NULL,
            license_key VARCHAR(255),
            licensed_to VARCHAR(200),
            start_date DATE,
            end_date DATE,
            note TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_asset_licenses_asset_id ON asset_licenses (asset_id)"
    )

    op.drop_column("asset_software", "license_type")
    op.drop_column("asset_software", "license_count")


def downgrade() -> None:
    op.add_column(
        "asset_software",
        sa.Column("license_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "asset_software",
        sa.Column("license_type", sa.String(50), nullable=True),
    )

    op.drop_table("asset_licenses")

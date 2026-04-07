"""AssetIP: replace asset_id with interface_id FK, drop legacy network columns.

Revision ID: 0064
Revises: 0063
"""
from alembic import op
import sqlalchemy as sa

revision = "0064"
down_revision = "0063"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old columns
    with op.batch_alter_table("asset_ips") as batch_op:
        batch_op.drop_index("ix_asset_ips_asset_id", if_exists=True)
        batch_op.drop_constraint("asset_ips_asset_id_fkey", type_="foreignkey")
        batch_op.drop_column("asset_id")
        batch_op.drop_column("interface_name")
        batch_op.drop_column("network")
        batch_op.drop_column("netmask")
        batch_op.drop_column("gateway")
        batch_op.drop_column("dns_primary")
        batch_op.drop_column("dns_secondary")

    # Add interface_id column with FK
    with op.batch_alter_table("asset_ips") as batch_op:
        batch_op.add_column(
            sa.Column(
                "interface_id",
                sa.Integer(),
                sa.ForeignKey("asset_interfaces.id", ondelete="CASCADE"),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_index("ix_asset_ips_interface_id", ["interface_id"])
        batch_op.create_unique_constraint(
            "uq_interface_ip", ["interface_id", "ip_address"]
        )


def downgrade() -> None:
    with op.batch_alter_table("asset_ips") as batch_op:
        batch_op.drop_constraint("uq_interface_ip", type_="unique")
        batch_op.drop_index("ix_asset_ips_interface_id")
        batch_op.drop_column("interface_id")

    with op.batch_alter_table("asset_ips") as batch_op:
        batch_op.add_column(sa.Column("asset_id", sa.Integer(), nullable=False))
        batch_op.add_column(sa.Column("interface_name", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("network", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("netmask", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("gateway", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("dns_primary", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("dns_secondary", sa.String(64), nullable=True))
        batch_op.create_foreign_key(
            "asset_ips_asset_id_fkey", "assets", ["asset_id"], ["id"]
        )
        batch_op.create_index("ix_asset_ips_asset_id", ["asset_id"])

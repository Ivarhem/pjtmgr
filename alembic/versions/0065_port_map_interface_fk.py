"""PortMap: replace asset/IP/text columns with interface FKs.

Revision ID: 0065
Revises: 0064
"""
from alembic import op
import sqlalchemy as sa

revision = "0065"
down_revision = "0064"
branch_labels = None
depends_on = None

# Columns removed from old model
_DROP_COLUMNS = [
    "src_asset_id",
    "dst_asset_id",
    "src_ip",
    "dst_ip",
    "src_mid",
    "src_rack_no",
    "src_rack_unit",
    "src_vendor",
    "src_model",
    "src_hostname",
    "src_cluster",
    "src_slot",
    "src_port_name",
    "src_service_name",
    "src_zone",
    "src_vlan",
    "dst_mid",
    "dst_rack_no",
    "dst_rack_unit",
    "dst_vendor",
    "dst_model",
    "dst_hostname",
    "dst_cluster",
    "dst_slot",
    "dst_port_name",
    "dst_service_name",
    "dst_zone",
    "dst_vlan",
]


def upgrade() -> None:
    with op.batch_alter_table("port_maps") as batch_op:
        # Drop FK constraints for old asset columns
        batch_op.drop_constraint("port_maps_src_asset_id_fkey", type_="foreignkey")
        batch_op.drop_constraint("port_maps_dst_asset_id_fkey", type_="foreignkey")

        # Drop all legacy columns
        for col in _DROP_COLUMNS:
            batch_op.drop_column(col)

        # Add interface FK columns
        batch_op.add_column(
            sa.Column(
                "src_interface_id",
                sa.Integer(),
                sa.ForeignKey("asset_interfaces.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "dst_interface_id",
                sa.Integer(),
                sa.ForeignKey("asset_interfaces.id", ondelete="SET NULL"),
                nullable=True,
            )
        )
        batch_op.create_index("ix_port_maps_src_interface_id", ["src_interface_id"])
        batch_op.create_index("ix_port_maps_dst_interface_id", ["dst_interface_id"])
        batch_op.create_unique_constraint(
            "uq_portmap_connection",
            ["src_interface_id", "dst_interface_id", "connection_type", "protocol", "port"],
        )


def downgrade() -> None:
    with op.batch_alter_table("port_maps") as batch_op:
        batch_op.drop_constraint("uq_portmap_connection", type_="unique")
        batch_op.drop_index("ix_port_maps_dst_interface_id")
        batch_op.drop_index("ix_port_maps_src_interface_id")
        batch_op.drop_column("dst_interface_id")
        batch_op.drop_column("src_interface_id")

    with op.batch_alter_table("port_maps") as batch_op:
        batch_op.add_column(sa.Column("src_asset_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("dst_asset_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("src_ip", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("dst_ip", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("src_mid", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("src_rack_no", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("src_rack_unit", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("src_vendor", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("src_model", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("src_hostname", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("src_cluster", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("src_slot", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("src_port_name", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("src_service_name", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("src_zone", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("src_vlan", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("dst_mid", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("dst_rack_no", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("dst_rack_unit", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("dst_vendor", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("dst_model", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("dst_hostname", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("dst_cluster", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("dst_slot", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("dst_port_name", sa.String(30), nullable=True))
        batch_op.add_column(sa.Column("dst_service_name", sa.String(200), nullable=True))
        batch_op.add_column(sa.Column("dst_zone", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("dst_vlan", sa.String(30), nullable=True))
        batch_op.create_foreign_key(
            "port_maps_src_asset_id_fkey", "assets", ["src_asset_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "port_maps_dst_asset_id_fkey", "assets", ["dst_asset_id"], ["id"]
        )

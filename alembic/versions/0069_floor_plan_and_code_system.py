"""Add floor plan grid, rack_lines table, system_id/project_code fields, and code system.

Revision ID: 0069
Revises: 0068
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- centers ---
    op.add_column("centers", sa.Column("system_id", sa.String(100), unique=True, nullable=True))
    op.add_column("centers", sa.Column("prefix", sa.String(10), nullable=True))
    op.add_column("centers", sa.Column("project_code", sa.String(100), nullable=True))
    op.create_index("ix_centers_system_id", "centers", ["system_id"], unique=True)

    # --- rooms ---
    op.add_column("rooms", sa.Column("system_id", sa.String(100), unique=True, nullable=True))
    op.add_column("rooms", sa.Column("prefix", sa.String(20), nullable=True))
    op.add_column("rooms", sa.Column("project_code", sa.String(100), nullable=True))
    op.add_column("rooms", sa.Column("grid_cols", sa.Integer(), nullable=False, server_default="10"))
    op.add_column("rooms", sa.Column("grid_rows", sa.Integer(), nullable=False, server_default="12"))
    op.create_index("ix_rooms_system_id", "rooms", ["system_id"], unique=True)

    # --- rack_lines ---
    op.create_table(
        "rack_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("line_name", sa.String(50), nullable=False),
        sa.Column("col_index", sa.Integer(), nullable=False),
        sa.Column("slot_count", sa.Integer(), nullable=False),
        sa.Column("disabled_slots", JSON, nullable=False, server_default="[]"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prefix", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "col_index", name="uq_rack_lines_room_col"),
    )
    op.create_index("ix_rack_lines_room_id", "rack_lines", ["room_id"])

    # --- racks ---
    op.add_column("racks", sa.Column("system_id", sa.String(100), unique=True, nullable=True))
    op.add_column("racks", sa.Column("project_code", sa.String(100), nullable=True))
    op.add_column(
        "racks",
        sa.Column(
            "rack_line_id",
            sa.Integer(),
            sa.ForeignKey("rack_lines.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("racks", sa.Column("line_position", sa.Integer(), nullable=True))
    op.create_index("ix_racks_system_id", "racks", ["system_id"], unique=True)

    # --- assets: rename asset_code → system_id, add project_code ---
    op.alter_column("assets", "asset_code", new_column_name="system_id")
    op.add_column("assets", sa.Column("project_code", sa.String(100), nullable=True))

    # --- asset_events: rename asset_code_snapshot → system_id_snapshot ---
    op.alter_column("asset_events", "asset_code_snapshot", new_column_name="system_id_snapshot")

    # --- contract_periods ---
    op.add_column(
        "contract_periods",
        sa.Column("rack_project_code_template", sa.String(200), nullable=True),
    )
    op.add_column(
        "contract_periods",
        sa.Column("asset_project_code_template", sa.String(200), nullable=True),
    )

    # --- Backfill system_id ---
    # centers: partner_code + '-' + center_code
    op.execute(
        """
        UPDATE centers c
        SET system_id = p.partner_code || '-' || c.center_code
        FROM partners p
        WHERE c.partner_id = p.id
          AND c.system_id IS NULL
        """
    )

    # rooms: center system_id + '-' + room_code
    op.execute(
        """
        UPDATE rooms r
        SET system_id = c.system_id || '-' || r.room_code
        FROM centers c
        WHERE r.center_id = c.id
          AND c.system_id IS NOT NULL
          AND r.system_id IS NULL
        """
    )

    # racks: room system_id + '-' + rack_code
    op.execute(
        """
        UPDATE racks rk
        SET system_id = rm.system_id || '-' || rk.rack_code
        FROM rooms rm
        WHERE rk.room_id = rm.id
          AND rm.system_id IS NOT NULL
          AND rk.system_id IS NULL
        """
    )


def downgrade() -> None:
    # contract_periods
    op.drop_column("contract_periods", "asset_project_code_template")
    op.drop_column("contract_periods", "rack_project_code_template")

    # asset_events
    op.alter_column("asset_events", "system_id_snapshot", new_column_name="asset_code_snapshot")

    # assets
    op.drop_column("assets", "project_code")
    op.alter_column("assets", "system_id", new_column_name="asset_code")

    # racks
    op.drop_index("ix_racks_system_id", table_name="racks")
    op.drop_column("racks", "line_position")
    op.drop_column("racks", "rack_line_id")
    op.drop_column("racks", "project_code")
    op.drop_column("racks", "system_id")

    # rack_lines
    op.drop_index("ix_rack_lines_room_id", table_name="rack_lines")
    op.drop_table("rack_lines")

    # rooms
    op.drop_index("ix_rooms_system_id", table_name="rooms")
    op.drop_column("rooms", "grid_rows")
    op.drop_column("rooms", "grid_cols")
    op.drop_column("rooms", "project_code")
    op.drop_column("rooms", "prefix")
    op.drop_column("rooms", "system_id")

    # centers
    op.drop_index("ix_centers_system_id", table_name="centers")
    op.drop_column("centers", "project_code")
    op.drop_column("centers", "prefix")
    op.drop_column("centers", "system_id")

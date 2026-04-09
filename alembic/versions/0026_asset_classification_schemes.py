"""add asset classification schemes

Revision ID: 0026
Revises: 0025
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("classification_schemes"):
        op.create_table(
            "classification_schemes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scope_type", sa.String(length=20), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=True),
            sa.Column("source_scheme_id", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["contract_periods.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_scheme_id"], ["classification_schemes.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("scope_type", "project_id", name="uq_classification_scheme_scope_project"),
        )
    scheme_indexes = {idx["name"] for idx in inspector.get_indexes("classification_schemes")}
    if op.f("ix_classification_schemes_project_id") not in scheme_indexes:
        op.create_index(op.f("ix_classification_schemes_project_id"), "classification_schemes", ["project_id"], unique=False)
    if op.f("ix_classification_schemes_scope_type") not in scheme_indexes:
        op.create_index(op.f("ix_classification_schemes_scope_type"), "classification_schemes", ["scope_type"], unique=False)
    if op.f("ix_classification_schemes_source_scheme_id") not in scheme_indexes:
        op.create_index(op.f("ix_classification_schemes_source_scheme_id"), "classification_schemes", ["source_scheme_id"], unique=False)

    if not inspector.has_table("classification_nodes"):
        op.create_table(
            "classification_nodes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scheme_id", sa.Integer(), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("node_code", sa.String(length=50), nullable=False),
            sa.Column("node_name", sa.String(length=120), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["parent_id"], ["classification_nodes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["scheme_id"], ["classification_schemes.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("scheme_id", "node_code", name="uq_classification_node_code"),
        )
    node_indexes = {idx["name"] for idx in inspector.get_indexes("classification_nodes")}
    if op.f("ix_classification_nodes_parent_id") not in node_indexes:
        op.create_index(op.f("ix_classification_nodes_parent_id"), "classification_nodes", ["parent_id"], unique=False)
    if op.f("ix_classification_nodes_scheme_id") not in node_indexes:
        op.create_index(op.f("ix_classification_nodes_scheme_id"), "classification_nodes", ["scheme_id"], unique=False)

    asset_columns = {col["name"] for col in inspector.get_columns("assets")}
    if "classification_node_id" not in asset_columns:
        op.add_column("assets", sa.Column("classification_node_id", sa.Integer(), nullable=True))
    asset_indexes = {idx["name"] for idx in inspector.get_indexes("assets")}
    if op.f("ix_assets_classification_node_id") not in asset_indexes:
        op.create_index(op.f("ix_assets_classification_node_id"), "assets", ["classification_node_id"], unique=False)
    asset_fks = {fk["constrained_columns"][0] for fk in inspector.get_foreign_keys("assets") if fk["constrained_columns"]}
    if "classification_node_id" not in asset_fks:
        op.create_foreign_key(
            None,
            "assets",
            "classification_nodes",
            ["classification_node_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_constraint(op.f("assets_classification_node_id_fkey"), "assets", type_="foreignkey")
    op.drop_index(op.f("ix_assets_classification_node_id"), table_name="assets")
    op.drop_column("assets", "classification_node_id")

    op.drop_index(op.f("ix_classification_nodes_scheme_id"), table_name="classification_nodes")
    op.drop_index(op.f("ix_classification_nodes_parent_id"), table_name="classification_nodes")
    op.drop_table("classification_nodes")

    op.drop_index(op.f("ix_classification_schemes_source_scheme_id"), table_name="classification_schemes")
    op.drop_index(op.f("ix_classification_schemes_scope_type"), table_name="classification_schemes")
    op.drop_index(op.f("ix_classification_schemes_project_id"), table_name="classification_schemes")
    op.drop_table("classification_schemes")

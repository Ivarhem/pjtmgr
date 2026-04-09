"""drop contract_period classification layout fk

Revision ID: 0061
Revises: 0060
"""
from alembic import op
import sqlalchemy as sa


revision = "0061"
down_revision = "0060"


def upgrade() -> None:
    op.drop_constraint(
        "fk_contract_periods_classification_layout_id",
        "contract_periods",
        type_="foreignkey",
    )


def downgrade() -> None:
    op.create_foreign_key(
        "fk_contract_periods_classification_layout_id",
        "contract_periods",
        "classification_layouts",
        ["classification_layout_id"],
        ["id"],
        ondelete="SET NULL",
    )

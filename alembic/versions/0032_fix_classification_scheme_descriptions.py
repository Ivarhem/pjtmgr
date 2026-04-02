"""fix broken classification scheme descriptions

Revision ID: 0032
Revises: 0031
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


GLOBAL_DESC = (
    "ISO/IEC 19770-1\uC758 IT \uC790\uC0B0\uAD00\uB9AC \uAD00\uC810\uACFC "
    "NIST CPE 2.3\uC758 \uC81C\uD488 \uC2DD\uBCC4 \uAD00\uC810\uC744 "
    "\uCC38\uACE0\uD574 \uC124\uACC4\uD55C \uAE00\uB85C\uBC8C \uAE30\uBCF8 "
    "\uBD84\uB958\uCCB4\uACC4"
)

PROJECT_DESC = (
    "\uD504\uB85C\uC81D\uD2B8\uBCC4 \uC790\uC0B0 \uC785\uB825\uACFC "
    "Import \uAC80\uC99D\uC5D0 \uC0AC\uC6A9\uD558\uB294 "
    "\uD504\uB85C\uC81D\uD2B8 \uBD84\uB958\uCCB4\uACC4"
)


def upgrade() -> None:
    conn = op.get_bind()
    schemes = sa.table(
        "classification_schemes",
        sa.column("id", sa.Integer),
        sa.column("scope_type", sa.String),
        sa.column("description", sa.Text),
    )

    conn.execute(
        sa.update(schemes)
        .where(
            schemes.c.scope_type == "global",
            sa.or_(
                schemes.c.description.is_(None),
                schemes.c.description.like("%?%"),
            ),
        )
        .values(description=GLOBAL_DESC)
    )
    conn.execute(
        sa.update(schemes)
        .where(
            schemes.c.scope_type == "project",
            sa.or_(
                schemes.c.description.is_(None),
                schemes.c.description.like("%?%"),
            ),
        )
        .values(description=PROJECT_DESC)
    )


def downgrade() -> None:
    pass

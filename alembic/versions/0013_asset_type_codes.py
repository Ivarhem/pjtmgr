"""Add asset_type_codes table and regenerate asset codes.

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"

_SEED = [
    ("server", "SVR", "서버", 1),
    ("network", "NET", "네트워크", 2),
    ("security", "SEC", "보안장비", 3),
    ("storage", "STO", "스토리지", 4),
    ("middleware", "MID", "미들웨어", 5),
    ("application", "APP", "응용", 6),
    ("other", "ETC", "기타", 7),
]

_TYPE_KEY_ALIASES = {"etc": "other"}
_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _to_base36(num: int, width: int = 4) -> str:
    if num == 0:
        return "0" * width
    result = ""
    while num:
        result = _BASE36[num % 36] + result
        num //= 36
    return result.zfill(width)


def upgrade() -> None:
    op.create_table(
        "asset_type_codes",
        sa.Column("type_key", sa.String(30), primary_key=True),
        sa.Column("code", sa.String(3), nullable=False),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )
    op.create_index("ix_asset_type_codes_code", "asset_type_codes", ["code"], unique=True)

    atc = sa.table(
        "asset_type_codes",
        sa.column("type_key", sa.String),
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(atc, [
        {"type_key": tk, "code": c, "label": l, "sort_order": s}
        for tk, c, l, s in _SEED
    ])

    conn = op.get_bind()
    assets_t = sa.table(
        "assets",
        sa.column("id", sa.Integer),
        sa.column("partner_id", sa.Integer),
        sa.column("asset_type", sa.String),
        sa.column("asset_code", sa.String),
    )
    partners_t = sa.table(
        "partners",
        sa.column("id", sa.Integer),
        sa.column("partner_code", sa.String),
    )

    type_code_map = {tk: c for tk, c, _, _ in _SEED}
    rows = conn.execute(
        sa.select(assets_t.c.id, assets_t.c.partner_id, assets_t.c.asset_type)
        .order_by(assets_t.c.id)
    ).fetchall()

    partner_codes = {}
    for r in conn.execute(sa.select(partners_t.c.id, partners_t.c.partner_code)).fetchall():
        partner_codes[r.id] = r.partner_code

    counters: dict[tuple[int, str], int] = {}
    for asset_id, partner_id, asset_type in rows:
        type_key = _TYPE_KEY_ALIASES.get(asset_type, asset_type)
        type_code = type_code_map.get(type_key, "ETC")
        partner_code = partner_codes.get(partner_id, "X000")

        key = (partner_id, type_code)
        seq = counters.get(key, 0)
        new_code = f"{partner_code}-{type_code}-{_to_base36(seq)}"
        counters[key] = seq + 1

        conn.execute(
            assets_t.update()
            .where(assets_t.c.id == asset_id)
            .values(asset_code=new_code)
        )


def downgrade() -> None:
    op.drop_index("ix_asset_type_codes_code", table_name="asset_type_codes")
    op.drop_table("asset_type_codes")

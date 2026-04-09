"""Add asset_type_key and is_placeholder to product_catalog, seed placeholders.

Revision ID: 0015
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"

# category -> asset_type_key 매핑
CATEGORY_MAP = {
    "server": "server", "서버": "server",
    "switch": "network", "스위치": "network",
    "router": "network", "라우터": "network",
    "firewall": "security", "방화벽": "security",
    "storage": "storage", "스토리지": "storage",
}

PLACEHOLDERS = [
    ("—", "미분류 서버", "Server", "server"),
    ("—", "미분류 네트워크장비", "Network", "network"),
    ("—", "미분류 보안장비", "Security", "security"),
    ("—", "미분류 스토리지", "Storage", "storage"),
    ("—", "미분류 미들웨어", "Middleware", "middleware"),
    ("—", "미분류 응용", "Application", "application"),
    ("—", "미분류 기타", "ETC", "other"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. 컬럼 추가 (dev 환경 create_all 대비: 컬럼 존재 여부 체크)
    has_col = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'product_catalog' AND column_name = 'asset_type_key'"
    )).scalar()
    if not has_col:
        op.add_column("product_catalog", sa.Column(
            "asset_type_key", sa.String(30),
            sa.ForeignKey("asset_type_codes.type_key", ondelete="SET NULL"),
            nullable=True,
        ))
        op.create_index("ix_product_catalog_asset_type_key", "product_catalog", ["asset_type_key"])

    has_col2 = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'product_catalog' AND column_name = 'is_placeholder'"
    )).scalar()
    if not has_col2:
        op.add_column("product_catalog", sa.Column(
            "is_placeholder", sa.Boolean(), nullable=False, server_default=sa.text("false"),
        ))

    # 2. 기존 데이터 category 기반 매핑
    for keyword, type_key in CATEGORY_MAP.items():
        conn.execute(sa.text(
            "UPDATE product_catalog SET asset_type_key = :tk "
            "WHERE asset_type_key IS NULL AND LOWER(category) LIKE :pattern"
        ), {"tk": type_key, "pattern": f"%{keyword}%"})

    # 3. Placeholder 시드 (vendor+name unique 제약 준수)
    for vendor, name, category, type_key in PLACEHOLDERS:
        exists = conn.execute(sa.text(
            "SELECT 1 FROM product_catalog WHERE vendor = :v AND name = :n"
        ), {"v": vendor, "n": name}).scalar()
        if not exists:
            conn.execute(sa.text(
                "INSERT INTO product_catalog (vendor, name, product_type, category, asset_type_key, is_placeholder) "
                "VALUES (:v, :n, 'hardware', :c, :tk, true)"
            ), {"v": vendor, "n": name, "c": category, "tk": type_key})


def downgrade() -> None:
    op.execute("DELETE FROM product_catalog WHERE is_placeholder = true")
    op.drop_index("ix_product_catalog_asset_type_key", "product_catalog")
    op.drop_column("product_catalog", "is_placeholder")
    op.drop_column("product_catalog", "asset_type_key")

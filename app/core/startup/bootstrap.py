"""시드 데이터 및 bootstrap 관리자 초기화."""
from __future__ import annotations

import logging

from app.core.config import (
    BOOTSTRAP_ADMIN_LOGIN_ID,
    BOOTSTRAP_ADMIN_NAME,
    BOOTSTRAP_ADMIN_PASSWORD,
    ENV,
)
from app.core.database import SessionLocal
from app.modules.common.services.contract_type_config import seed_defaults as seed_contract_types
from app.modules.common.services.asset_type_code import seed_defaults as seed_asset_type_codes
from app.modules.common.services.term_config import seed_defaults as seed_terms
from app.modules.common.services.user import ensure_bootstrap_admin

logger = logging.getLogger("sales")

# ── 기본 시스템 역할 정의 ──────────────────────────────────────

SYSTEM_ROLES: list[dict] = [
    {
        "name": "관리자",
        "is_system": True,
        "permissions": {
            "admin": True,
            "modules": {"accounting": "full", "infra": "full"},
        },
    },
    {
        "name": "영업담당자",
        "is_system": True,
        "permissions": {
            "admin": False,
            "modules": {"accounting": "full"},
        },
    },
    {
        "name": "기술담당자",
        "is_system": True,
        "permissions": {
            "admin": False,
            "modules": {"infra": "full"},
        },
    },
    {
        "name": "PM",
        "is_system": True,
        "permissions": {
            "admin": False,
            "modules": {"accounting": "full", "infra": "full"},
        },
    },
]


def seed_system_roles(db) -> None:
    """시스템 기본 역할을 생성한다 (멱등)."""
    from app.modules.common.models.role import Role

    for role_data in SYSTEM_ROLES:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            logger.info("시스템 역할 생성: %s", role_data["name"])
    db.commit()


def get_admin_role_id(db) -> int:
    """관리자 역할의 ID를 반환."""
    from app.modules.common.models.role import Role

    role = db.query(Role).filter(Role.name == "관리자").first()
    if not role:
        raise RuntimeError("관리자 역할이 존재하지 않습니다. seed_system_roles()를 먼저 실행하세요.")
    return role.id


def initialize_reference_data() -> None:
    """기본 참조 데이터와 bootstrap 관리자 계정을 준비한다."""
    db = SessionLocal()
    try:
        # 역할 시딩 (가장 먼저 — 사용자 생성에 필요)
        seed_system_roles(db)

        seed_contract_types(db)
        seed_asset_type_codes(db)
        seed_terms(db)

        admin_role_id = get_admin_role_id(db)
        admin = ensure_bootstrap_admin(
            db,
            login_id=BOOTSTRAP_ADMIN_LOGIN_ID,
            password=BOOTSTRAP_ADMIN_PASSWORD,
            name=BOOTSTRAP_ADMIN_NAME,
            role_id=admin_role_id,
        )
        if admin:
            logger.info("초기 관리자 계정을 생성했습니다. login_id=%s", admin.login_id)
        elif ENV != "dev":
            logger.info("초기 관리자 bootstrap 미설정 상태로 시작했습니다.")
    finally:
        db.close()

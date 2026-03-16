"""시드 데이터 및 bootstrap 관리자 초기화."""
from __future__ import annotations

import logging

from app.config import (
    BOOTSTRAP_ADMIN_LOGIN_ID,
    BOOTSTRAP_ADMIN_NAME,
    BOOTSTRAP_ADMIN_PASSWORD,
    ENV,
)
from app.database import SessionLocal
from app.services.contract_type_config import seed_defaults as seed_contract_types
from app.services.term_config import seed_defaults as seed_terms
from app.services.user import ensure_bootstrap_admin

logger = logging.getLogger("sales")


def initialize_reference_data() -> None:
    """기본 참조 데이터와 bootstrap 관리자 계정을 준비한다."""
    db = SessionLocal()
    try:
        seed_contract_types(db)
        seed_terms(db)
        admin = ensure_bootstrap_admin(
            db,
            login_id=BOOTSTRAP_ADMIN_LOGIN_ID,
            password=BOOTSTRAP_ADMIN_PASSWORD,
            name=BOOTSTRAP_ADMIN_NAME,
        )
        if admin:
            logger.info("초기 관리자 계정을 생성했습니다. login_id=%s", admin.login_id)
        elif ENV != "dev":
            logger.info("초기 관리자 bootstrap 미설정 상태로 시작했습니다.")
    finally:
        db.close()

"""Health check service."""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def check_health(db: Session) -> dict:
    """서비스 상태 및 DB 연결 확인."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("헬스체크 DB 확인 실패")
        return {"status": "degraded", "db": "unavailable"}

    return {"status": "ok", "db": "ok"}

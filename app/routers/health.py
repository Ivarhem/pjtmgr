"""Health check endpoint for container orchestrators."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """서비스 상태 및 DB 연결 확인."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("헬스체크 DB 확인 실패")
        return {"status": "degraded", "db": "unavailable"}

    return {"status": "ok", "db": "ok"}

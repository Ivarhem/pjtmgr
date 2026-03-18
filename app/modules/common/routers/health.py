"""Health check endpoint for container orchestrators."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.common.services import health as svc

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """서비스 상태 및 DB 연결 확인."""
    return svc.check_health(db)

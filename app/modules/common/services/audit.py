"""감사 로그 기록 유틸리티."""
from __future__ import annotations
from sqlalchemy.orm import Session
from app.modules.common.models.audit_log import AuditLog


def log(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    summary: str | None = None,
    detail: str | None = None,
) -> None:
    """감사 로그 1건을 기록한다. flush만 수행 (commit은 호출자 트랜잭션에 맡김)."""
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        detail=detail,
    ))
    db.flush()

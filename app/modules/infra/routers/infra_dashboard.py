"""Infra dashboard API — aggregation endpoints for status board and summary cards."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.audit_log import AuditLog
from app.modules.common.models.user import User
from app.modules.infra.services.infra_metrics import (
    list_projects_summary,
    get_non_compliant_assignments,
    get_project_summary,
    get_unsubmitted_deliverables,
)

router = APIRouter(prefix="/api/v1/infra-dashboard", tags=["infra-dashboard"])


@router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    return list_projects_summary(db)


@router.get("/project/{project_id}")
def project_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    return get_project_summary(db, project_id)


@router.get("/unsubmitted")
def unsubmitted_deliverables(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    return get_unsubmitted_deliverables(db)


@router.get("/non-compliant")
def non_compliant_policies(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    return get_non_compliant_assignments(db)


@router.get("/audit-log")
def audit_log_list(
    project_id: int | None = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    """인프라 모듈 감사 로그 조회."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.module == "infra")
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    logs = list(db.scalars(stmt))
    # user name enrichment
    user_ids = {l.user_id for l in logs if l.user_id}
    users = {}
    if user_ids:
        users = {
            u.id: u.name
            for u in db.scalars(select(User).where(User.id.in_(user_ids)))
        }
    return [
        {
            "id": l.id,
            "user_name": users.get(l.user_id, "-"),
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "summary": l.summary,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]

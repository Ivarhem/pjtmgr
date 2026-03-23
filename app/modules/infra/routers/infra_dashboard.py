"""Infra dashboard API — aggregation endpoints for status board and summary cards."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.services.infra_metrics import (
    get_non_compliant_assignments,
    get_period_summary,
    get_unsubmitted_deliverables,
    list_audit_logs,
    list_periods_summary,
)

router = APIRouter(prefix="/api/v1/infra-dashboard", tags=["infra-dashboard"])


@router.get("/summary")
def dashboard_summary(
    customer_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    return list_periods_summary(db, customer_id=customer_id)


@router.get("/period/{contract_period_id}")
def period_summary(
    contract_period_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    return get_period_summary(db, contract_period_id)


@router.get("/unsubmitted")
def unsubmitted_deliverables(
    customer_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    return get_unsubmitted_deliverables(db, customer_id=customer_id)


@router.get("/non-compliant")
def non_compliant_policies(
    customer_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    return get_non_compliant_assignments(db, customer_id=customer_id)


@router.get("/audit-log")
def audit_log_list(
    contract_period_id: int | None = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[dict]:
    """인프라 모듈 감사 로그 조회."""
    return list_audit_logs(db, module="infra", contract_period_id=contract_period_id, limit=limit)

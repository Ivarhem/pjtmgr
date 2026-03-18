"""Infra dashboard API — aggregation endpoints for status board and summary cards."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.services.infra_metrics import (
    get_all_projects_summary,
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
    return get_all_projects_summary(db)


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

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.schemas.report import TargetVsActualResponse
from app.services import dashboard as svc

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
def get_dashboard_summary(
    date_from: str | None = Query(None, description="시작월 (YYYY-MM)"),
    date_to: str | None = Query(None, description="종료월 (YYYY-MM)"),
    owner_id: Annotated[list[int] | None, Query()] = None,
    department: Annotated[list[str] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    stage: Annotated[list[str] | None, Query()] = None,
    customer_id: Annotated[list[int] | None, Query()] = None,
    group_by: Literal["month", "quarter", "half", "year"] = Query("month", description="집계 단위"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """대시보드 전체 데이터 조회."""
    return svc.get_dashboard(
        db,
        date_from=date_from,
        date_to=date_to,
        owner_id=owner_id,
        department=department,
        contract_type=contract_type,
        stage=stage,
        customer_id=customer_id,
        group_by=group_by,
        current_user=current_user,
    )


@router.get("/target-vs-actual", response_model=TargetVsActualResponse)
def get_target_vs_actual(
    date_from: str | None = Query(None, description="시작월 (YYYY-MM)"),
    date_to: str | None = Query(None, description="종료월 (YYYY-MM)"),
    owner_id: Annotated[list[int] | None, Query()] = None,
    department: Annotated[list[str] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    customer_id: Annotated[list[int] | None, Query()] = None,
    group_by: Literal["month", "quarter", "half", "year"] = Query("month", description="집계 단위"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TargetVsActualResponse:
    """매출 목표 vs 실적 비교 조회."""
    return svc.get_target_vs_actual(
        db,
        date_from=date_from,
        date_to=date_to,
        owner_id=owner_id,
        department=department,
        contract_type=contract_type,
        customer_id=customer_id,
        group_by=group_by,
        current_user=current_user,
    )

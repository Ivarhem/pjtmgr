"""대시보드 서비스.

metrics.py의 공통 집계 함수를 조합하여 대시보드 데이터를 구성한다.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.services.metrics import (
    build_filter,
    aggregate_totals,
    aggregate_monthly_trend,
    aggregate_by_field,
    top_customers,
    ar_warnings,
)

if TYPE_CHECKING:
    from app.models.user import User


def _default_date_from() -> str:
    return f"{datetime.date.today().year}-01"


def _default_date_to() -> str:
    return f"{datetime.date.today().year}-12"


def get_dashboard(
    db: Session,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    owner_id: list[int] | None = None,
    department: list[str] | None = None,
    contract_type: list[str] | None = None,
    stage: list[str] | None = None,
    current_user: User | None = None,
) -> dict:
    """대시보드 전체 데이터.

    Args:
        date_from: 시작월 (YYYY-MM). 미지정 시 올해 1월.
        date_to: 종료월 (YYYY-MM). 미지정 시 올해 12월.
        owner_id, department, contract_type, stage: 선택적 필터.

    반환:
        kpis, monthly_trend, by_type, by_department, top_customers, ar_warnings
    """
    filt = build_filter(
        date_from or _default_date_from(),
        date_to or _default_date_to(),
        owner_id=owner_id,
        department=department,
        contract_type=contract_type,
        stage=stage,
    )

    label = f"{filt.date_from[:4]}"
    if filt.date_from[:4] != filt.date_to[:4]:
        label = f"{filt.date_from[:7]} ~ {filt.date_to[:7]}"

    return {
        "year": label,
        "kpis": aggregate_totals(db, filt, current_user),
        "monthly_trend": aggregate_monthly_trend(db, filt, current_user),
        "by_type": aggregate_by_field(db, filt, current_user, "contract_type"),
        "by_department": aggregate_by_field(db, filt, current_user, "department"),
        "top_customers": top_customers(db, filt, current_user, n=10),
        "ar_warnings": ar_warnings(db, filt, current_user, n=10),
    }

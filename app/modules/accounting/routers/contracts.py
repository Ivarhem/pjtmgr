"""Accounting-specific 라우터: 원장 목록, Ledger, 내 사업 요약.

Common Contract/Period CRUD는 app.modules.common.routers.contracts로 이관됨.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.accounting.services import contract as svc
from app.modules.accounting.services import ledger as ledger_svc
from app.modules.accounting.services.dashboard import get_my_contracts_summary

router = APIRouter(prefix="/api/v1", tags=["contracts"])


# ── 원장 목록 (contract_periods + contracts + sales_detail JOIN) ──────
@router.get("/ledger/periods")
def list_ledger_periods(
    period_year: Annotated[list[int] | None, Query()] = None,
    calendar_year: Annotated[list[int] | None, Query()] = None,
    contract_type: Annotated[list[str] | None, Query()] = None,
    stage: Annotated[list[str] | None, Query()] = None,
    owner_department: Annotated[list[str] | None, Query()] = None,
    owner_id: Annotated[list[int] | None, Query()] = None,
    active_month: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return svc.list_periods_flat(
        db,
        period_year=period_year,
        calendar_year=calendar_year,
        contract_type=contract_type,
        stage=stage,
        owner_department=owner_department,
        owner_id=owner_id,
        current_user=current_user,
        active_month=active_month,
    )


# ── Ledger (TransactionLine + Receipt 병합 뷰) ─────────────────────────
@router.get("/contracts/{contract_id}/ledger")
def get_ledger(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return ledger_svc.get_ledger(db, contract_id, current_user=current_user)


# ── 내 사업 요약 ─────────────────────────────────────────────
@router.get("/my-contracts/summary")
def my_contracts_summary(
    period_year: Annotated[list[int] | None, Query()] = None,
    calendar_year: Annotated[list[int] | None, Query()] = None,
    active_month: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """현재 사용자의 사업 요약 (진행 사업 수, 매출, GP%, 미수금)."""
    return get_my_contracts_summary(
        db,
        current_user,
        period_year=period_year,
        calendar_year=calendar_year,
        active_month=active_month,
    )

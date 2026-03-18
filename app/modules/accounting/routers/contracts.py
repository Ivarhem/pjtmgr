"""Contract / ContractPeriod CRUD + Ledger + 내 사업 요약 라우터."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_admin, require_module_access
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.accounting.schemas.contract import (
    BulkAssignOwnerRequest,
    ContractCreate,
    ContractPeriodCreate,
    ContractPeriodUpdate,
    ContractRead,
    ContractUpdate,
)
from app.modules.accounting.services import contract as svc
from app.modules.accounting.services import ledger as ledger_svc
from app.modules.accounting.services.dashboard import get_my_contracts_summary

router = APIRouter(prefix="/api/v1", tags=["contracts"])


# ── 원장 목록 (contract_periods + contracts JOIN) ─────────────────────
@router.get("/contract-periods")
def list_contract_periods(
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


# ── Contract CRUD ─────────────────────────────────────────────────
@router.get("/contracts/{contract_id}", response_model=ContractRead)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractRead:
    return svc.get_contract(db, contract_id, current_user=current_user)


@router.post("/contracts", response_model=ContractRead, status_code=201, dependencies=[require_module_access("accounting", "full")])
def create_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractRead:
    return svc.create_contract(db, data, created_by=current_user.id)


@router.patch("/contracts/{contract_id}", response_model=ContractRead, dependencies=[require_module_access("accounting", "full")])
def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractRead:
    return svc.update_contract(db, contract_id, data, current_user=current_user)


@router.post("/contracts/bulk-assign-owner")
def bulk_assign_owner(
    body: BulkAssignOwnerRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """선택한 사업들의 담당자를 일괄 변경 (관리자 전용)."""
    if not body.contract_ids:
        return {"updated": 0}
    count = svc.bulk_assign_owner(db, body.contract_ids, body.owner_user_id)
    return {"updated": count}


@router.delete("/contracts/{contract_id}", status_code=204)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_contract(db, contract_id)


@router.post("/contracts/{contract_id}/restore")
def restore_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    return svc.restore_contract(db, contract_id)


# ── ContractPeriod CRUD ───────────────────────────────────────────
@router.get("/contracts/{contract_id}/periods")
def list_contract_periods_for_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return svc.get_contract_periods(db, contract_id, current_user=current_user)


@router.get("/contract-periods/{period_id}")
def get_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.get_period(db, period_id, current_user=current_user)


@router.post("/contracts/{contract_id}/periods", status_code=201, dependencies=[require_module_access("accounting", "full")])
def create_period(
    contract_id: int,
    data: ContractPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.create_period(db, contract_id, data, current_user=current_user)


@router.patch("/contract-periods/{period_id}", dependencies=[require_module_access("accounting", "full")])
def update_period(
    period_id: int,
    data: ContractPeriodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.update_period(db, period_id, data, current_user=current_user)


@router.delete("/contract-periods/{period_id}", status_code=204, dependencies=[require_module_access("accounting", "full")])
def delete_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    svc.delete_period(db, period_id, current_user=current_user)


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

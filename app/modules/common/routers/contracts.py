"""Contract / ContractPeriod CRUD 공통 라우터."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.common.schemas.contract import (
    BulkAssignOwnerRequest,
    ContractCreate,
    ContractRead,
    ContractUpdate,
)
from app.modules.common.schemas.contract_period import (
    ContractPeriodCreate,
    ContractPeriodUpdate,
)
from app.modules.common.services import contract_service as svc

router = APIRouter(prefix="/api/v1", tags=["contracts"])


# ── Contract-Period 목록 (customer_id 필터 지원) ─────────────────────────
@router.get("/contract-periods")
def list_contract_periods(
    customer_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return svc.list_periods(db, customer_id=customer_id)


# ── Contract CRUD ─────────────────────────────────────────────────
@router.get("/contracts/{contract_id}", response_model=ContractRead)
def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractRead:
    return svc.get_contract(db, contract_id, current_user=current_user)


@router.post("/contracts", response_model=ContractRead, status_code=201)
def create_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ContractRead:
    return svc.create_contract(db, data, created_by=_admin.id)


@router.patch("/contracts/{contract_id}", response_model=ContractRead)
def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ContractRead:
    return svc.update_contract(db, contract_id, data, current_user=_admin)


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


@router.post("/contracts/{contract_id}/periods", status_code=201)
def create_period(
    contract_id: int,
    data: ContractPeriodCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    return svc.create_period(db, contract_id, data, current_user=_admin)


@router.get("/contract-periods/{period_id}")
def get_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.get_period(db, period_id, current_user=current_user)


@router.patch("/contract-periods/{period_id}")
def update_period(
    period_id: int,
    data: ContractPeriodUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    return svc.update_period(db, period_id, data, current_user=_admin)


@router.delete("/contract-periods/{period_id}", status_code=204)
def delete_period(
    period_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_period(db, period_id, current_user=_admin)

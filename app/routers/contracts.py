from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.auth.authorization import check_contract_access, check_period_access
from app.models.user import User
from app.schemas.contract import (
    ContractCreate, ContractUpdate, ContractRead,
    ContractPeriodCreate, ContractPeriodUpdate, ContractPeriodRead, ContractPeriodListRead,
    BulkAssignOwnerRequest,
)
from app.schemas.monthly_forecast import MonthlyForecastCreate, MonthlyForecastRead
from app.schemas.transaction_line import TransactionLineCreate, TransactionLineUpdate, TransactionLineRead
from app.schemas.receipt import ReceiptCreate, ReceiptUpdate, ReceiptRead
from app.schemas.receipt_match import ReceiptMatchCreate, ReceiptMatchUpdate
from app.services import contract as svc
from app.services import receipt_match as match_svc

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
):
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
):
    check_contract_access(db, contract_id, current_user)
    return svc.get_contract(db, contract_id)


@router.post("/contracts", response_model=ContractRead, status_code=201)
def create_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.create_contract(db, data, created_by=current_user.id)


@router.patch("/contracts/{contract_id}", response_model=ContractRead)
def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.update_contract(db, contract_id, data)


@router.post("/contracts/bulk-assign-owner")
def bulk_assign_owner(
    body: BulkAssignOwnerRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
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
):
    svc.delete_contract(db, contract_id)


@router.post("/contracts/{contract_id}/restore")
def restore_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return svc.restore_contract(db, contract_id)


# ── ContractPeriod CRUD ───────────────────────────────────────────
@router.get("/contracts/{contract_id}/periods")
def list_contract_periods_for_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.get_contract_periods(db, contract_id)


@router.get("/contract-periods/{period_id}")
def get_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_period_access(db, period_id, current_user)
    return svc.get_period(db, period_id)


@router.post("/contracts/{contract_id}/periods", status_code=201)
def create_period(
    contract_id: int,
    data: ContractPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.create_period(db, contract_id, data)


@router.patch("/contract-periods/{period_id}")
def update_period(
    period_id: int,
    data: ContractPeriodUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_period_access(db, period_id, current_user)
    return svc.update_period(db, period_id, data)



@router.delete("/contract-periods/{period_id}", status_code=204)
def delete_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_period_access(db, period_id, current_user)
    svc.delete_period(db, period_id)


# ── Forecasts ─────────────────────────────────────────────────
@router.get("/contract-periods/{period_id}/forecasts", response_model=list[MonthlyForecastRead])
def get_forecasts(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_period_access(db, period_id, current_user)
    return svc.get_forecasts(db, period_id)


@router.get("/contracts/{contract_id}/all-forecasts")
def list_all_forecasts(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.list_all_forecasts(db, contract_id)


@router.patch("/contract-periods/{period_id}/forecasts", response_model=list[MonthlyForecastRead])
def upsert_forecasts(
    period_id: int,
    items: list[MonthlyForecastCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_period_access(db, period_id, current_user)
    return svc.upsert_forecasts(db, period_id, items, created_by=current_user.id)


# ── Transaction Lines ───────────────────────────────────────────────────
@router.get("/contracts/{contract_id}/transaction-lines")
def get_transaction_lines(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.get_transaction_lines(db, contract_id)


@router.post("/contracts/{contract_id}/transaction-lines", status_code=201)
def create_transaction_line(
    contract_id: int,
    data: TransactionLineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.create_transaction_line(db, contract_id, data, created_by=current_user.id)


@router.patch("/transaction-lines/{transaction_line_id}")
def update_transaction_line(
    transaction_line_id: int,
    data: TransactionLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.update_transaction_line(db, transaction_line_id, data, current_user=current_user)


@router.delete("/transaction-lines/{transaction_line_id}", status_code=204)
def delete_transaction_line(
    transaction_line_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    svc.delete_transaction_line(db, transaction_line_id)


@router.post("/contracts/{contract_id}/transaction-lines/bulk-confirm")
def bulk_confirm_transaction_lines(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """거래처+발행일이 있는 '예정' 행을 일괄 확정 처리."""
    check_contract_access(db, contract_id, current_user)
    return svc.bulk_confirm_transaction_lines(db, contract_id)


# ── Receipts ──────────────────────────────────────────────────
@router.get("/contracts/{contract_id}/receipts")
def get_receipts(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.get_receipts(db, contract_id)


@router.post("/contracts/{contract_id}/receipts", status_code=201)
def create_receipt(
    contract_id: int,
    data: ReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.create_receipt(db, contract_id, data, created_by=current_user.id)


@router.patch("/receipts/{receipt_id}")
def update_receipt(
    receipt_id: int,
    data: ReceiptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return svc.update_receipt(db, receipt_id, data, current_user=current_user)


@router.delete("/receipts/{receipt_id}", status_code=204)
def delete_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    svc.delete_receipt(db, receipt_id)


# ── Receipt Matches ──────────────────────────────────────────
@router.get("/contracts/{contract_id}/receipt-matches")
def list_matches(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return match_svc.list_matches_by_contract(db, contract_id)


@router.post("/contracts/{contract_id}/receipt-matches", status_code=201)
def create_match(
    contract_id: int,
    data: ReceiptMatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return match_svc.create_match(db, data, created_by=current_user.id)


@router.patch("/receipt-matches/{match_id}")
def update_match(
    match_id: int,
    data: ReceiptMatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return match_svc.update_match(db, match_id, data)


@router.delete("/receipt-matches/{match_id}", status_code=204)
def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match_svc.delete_match(db, match_id)


@router.post("/contracts/{contract_id}/receipt-matches/auto", status_code=200)
def auto_match(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """FIFO 자동 배분 재실행."""
    check_contract_access(db, contract_id, current_user)
    match_svc.auto_match_contract(db, contract_id, created_by=current_user.id)
    return match_svc.list_matches_by_contract(db, contract_id)


# ── Forecast → TransactionLine 동기화 ──────────────────────────────────
@router.get("/contracts/{contract_id}/forecast-sync-preview")
def preview_forecast_sync(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast ↔ TransactionLine 대조 미리보기 (전체 period)."""
    check_contract_access(db, contract_id, current_user)
    return svc.preview_forecast_sync(db, contract_id)


@router.post("/contracts/{contract_id}/forecast-sync", status_code=200)
def sync_transaction_lines_from_forecast(
    contract_id: int,
    body: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast 기반 TransactionLine 동기화 (전체 period): 생성 + 선택 삭제."""
    check_contract_access(db, contract_id, current_user)
    delete_ids = (body or {}).get("delete_ids", [])
    return svc.sync_transaction_lines_from_forecast(db, contract_id, delete_ids)


# ── Ledger (TransactionLine + Receipt 병합 뷰) ─────────────────────────
@router.get("/contracts/{contract_id}/ledger")
def get_ledger(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_contract_access(db, contract_id, current_user)
    return svc.get_ledger(db, contract_id)


# ── 내 사업 요약 ─────────────────────────────────────────────
@router.get("/my-contracts/summary")
def get_my_contracts_summary(
    period_year: Annotated[list[int] | None, Query()] = None,
    calendar_year: Annotated[list[int] | None, Query()] = None,
    active_month: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """현재 사용자의 사업 요약 (진행 사업 수, 매출, GP%, 미수금)."""
    return svc.get_my_contracts_summary(
        db, current_user, period_year=period_year, calendar_year=calendar_year,
        active_month=active_month,
    )

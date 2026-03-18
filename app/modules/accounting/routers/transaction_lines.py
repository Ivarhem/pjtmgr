"""TransactionLine(매출/매입 실적) 라우터."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.accounting.schemas.transaction_line import (
    TransactionLineCreate,
    TransactionLineUpdate,
)
from app.modules.accounting.services import transaction_line as svc

router = APIRouter(prefix="/api/v1", tags=["transaction-lines"])


@router.get("/contracts/{contract_id}/transaction-lines")
def get_transaction_lines(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return svc.list_transaction_lines_for_contract(db, contract_id, current_user=current_user)


@router.post("/contracts/{contract_id}/transaction-lines", status_code=201)
def create_transaction_line(
    contract_id: int,
    data: TransactionLineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.create_transaction_line(
        db,
        contract_id,
        data,
        created_by=current_user.id,
        current_user=current_user,
    )


@router.patch("/transaction-lines/{transaction_line_id}")
def update_transaction_line(
    transaction_line_id: int,
    data: TransactionLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.update_transaction_line(db, transaction_line_id, data, current_user=current_user)


@router.delete("/transaction-lines/{transaction_line_id}", status_code=204)
def delete_transaction_line(
    transaction_line_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_transaction_line(db, transaction_line_id)


@router.post("/contracts/{contract_id}/transaction-lines/bulk-confirm")
def bulk_confirm_transaction_lines(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """거래처+발행일이 있는 '예정' 행을 일괄 확정 처리."""
    return svc.bulk_confirm_transaction_lines(db, contract_id, current_user=current_user)

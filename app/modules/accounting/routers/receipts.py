"""Receipt(입금) 라우터."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.accounting.schemas.receipt import ReceiptCreate, ReceiptUpdate
from app.modules.accounting.services import receipt as svc

router = APIRouter(prefix="/api/v1", tags=["receipts"])


@router.get("/contracts/{contract_id}/receipts")
def get_receipts(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return svc.list_receipts_for_contract(db, contract_id, current_user=current_user)


@router.post("/contracts/{contract_id}/receipts", status_code=201)
def create_receipt(
    contract_id: int,
    data: ReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.create_receipt(
        db,
        contract_id,
        data,
        created_by=current_user.id,
        current_user=current_user,
    )


@router.patch("/receipts/{receipt_id}")
def update_receipt(
    receipt_id: int,
    data: ReceiptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.update_receipt(db, receipt_id, data, current_user=current_user)


@router.delete("/receipts/{receipt_id}", status_code=204)
def delete_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_receipt(db, receipt_id)

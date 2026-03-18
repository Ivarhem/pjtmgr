"""ReceiptMatch(입금 배분) 라우터."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.authorization import check_contract_access
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.receipt_match import ReceiptMatchCreate, ReceiptMatchUpdate
from app.services import receipt_match as match_svc

router = APIRouter(prefix="/api/v1", tags=["receipt-matches"])


@router.get("/contracts/{contract_id}/receipt-matches")
def list_matches(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    check_contract_access(db, contract_id, current_user)
    return match_svc.list_matches_by_contract(db, contract_id)


@router.post("/contracts/{contract_id}/receipt-matches", status_code=201)
def create_match(
    contract_id: int,
    data: ReceiptMatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    check_contract_access(db, contract_id, current_user)
    return match_svc.create_match(
        db,
        data,
        created_by=current_user.id,
        current_user=current_user,
        expected_contract_id=contract_id,
    )


@router.patch("/receipt-matches/{match_id}")
def update_match(
    match_id: int,
    data: ReceiptMatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return match_svc.update_match(db, match_id, data, current_user=current_user)


@router.delete("/receipt-matches/{match_id}", status_code=204)
def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    match_svc.delete_match(db, match_id, current_user=current_user)


@router.post("/contracts/{contract_id}/receipt-matches/auto", status_code=200)
def auto_match(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """FIFO 자동 배분 재실행."""
    check_contract_access(db, contract_id, current_user)
    match_svc.auto_match_contract(db, contract_id, created_by=current_user.id)
    return match_svc.list_matches_by_contract(db, contract_id)

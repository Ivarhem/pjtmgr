from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.common.schemas.customer import CustomerCreate, CustomerUpdate, CustomerRead, CustomerListRead
from app.modules.common.schemas.customer_contact import CustomerContactCreate, CustomerContactUpdate
from app.modules.common.services import customer as svc
from app.core.auth.dependencies import get_current_user, require_admin
from app.modules.common.models.user import User

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("", response_model=list[CustomerListRead])
def list_customers(
    my_only: bool = False,
    customer_type: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CustomerListRead]:
    return svc.list_customers(db, current_user=current_user, my_only=my_only, customer_type=customer_type)


@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> CustomerRead:
    return svc.create_customer(db, data)


@router.get("/{customer_id}/contracts")
def list_customer_contracts(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return svc.list_related_contracts(db, customer_id, current_user=current_user)


@router.get("/{customer_id}/financials")
def list_customer_financials(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.list_customer_financials(db, customer_id, current_user=current_user)


@router.get("/{customer_id}/receipts")
def list_customer_receipts(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return svc.list_customer_receipts(db, customer_id, current_user=current_user)


@router.delete("/{customer_id}", status_code=204)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_customer(db, customer_id)


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> CustomerRead:
    return svc.update_customer(db, customer_id, data)


# ── 담당자 (CustomerContact) ─────────────────────────────────


@router.get("/{customer_id}/contacts")
def list_contacts(customer_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[dict]:
    return svc.get_contacts(db, customer_id)


@router.post("/{customer_id}/contacts", status_code=201)
def create_contact(customer_id: int, data: CustomerContactCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return svc.create_contact(db, customer_id, data)


@router.patch("/contacts/{contact_id}")
def update_contact(contact_id: int, data: CustomerContactUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict:
    return svc.update_contact(db, contact_id, data)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> None:
    svc.delete_contact(db, contact_id)

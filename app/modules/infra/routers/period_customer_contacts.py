from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.period_customer_contact import (
    PeriodCustomerContactCreate,
    PeriodCustomerContactRead,
    PeriodCustomerContactUpdate,
)
from app.modules.infra.services import period_customer_contact_service as svc

router = APIRouter(
    prefix="/api/v1/period-customer-contacts",
    tags=["infra-period-customer-contacts"],
)


@router.get("", response_model=list[PeriodCustomerContactRead])
def list_period_customer_contacts(
    period_customer_id: int | None = None,
    contract_period_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PeriodCustomerContactRead]:
    if contract_period_id:
        return svc.list_by_period(db, contract_period_id)
    if period_customer_id:
        return svc.list_by_period_customer(db, period_customer_id)
    return []


@router.post(
    "", response_model=PeriodCustomerContactRead, status_code=status.HTTP_201_CREATED
)
def create_period_customer_contact(
    payload: PeriodCustomerContactCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pcc = svc.create_period_customer_contact(db, payload, current_user)
    enriched = svc.list_by_period_customer(db, pcc.period_customer_id)
    return next((r for r in enriched if r["id"] == pcc.id), enriched[0])


@router.patch("/{link_id}", response_model=PeriodCustomerContactRead)
def update_period_customer_contact(
    link_id: int,
    payload: PeriodCustomerContactUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pcc = svc.update_period_customer_contact(db, link_id, payload, current_user)
    enriched = svc.list_by_period_customer(db, pcc.period_customer_id)
    return next((r for r in enriched if r["id"] == pcc.id), enriched[0])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period_customer_contact(
    link_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc.delete_period_customer_contact(db, link_id, current_user)

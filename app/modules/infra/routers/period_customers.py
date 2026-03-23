from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.period_customer import (
    PeriodCustomerCreate,
    PeriodCustomerRead,
    PeriodCustomerUpdate,
)
from app.modules.infra.services import period_customer_service as svc

router = APIRouter(prefix="/api/v1/period-customers", tags=["infra-period-customers"])


@router.get("", response_model=list[PeriodCustomerRead])
def list_period_customers(
    contract_period_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PeriodCustomerRead]:
    return svc.list_by_period(db, contract_period_id)


@router.post("", response_model=PeriodCustomerRead, status_code=status.HTTP_201_CREATED)
def create_period_customer(
    payload: PeriodCustomerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pc = svc.create_period_customer(db, payload, current_user)
    enriched = svc.list_by_period(db, pc.contract_period_id)
    return next((r for r in enriched if r["id"] == pc.id), enriched[0])


@router.patch("/{link_id}", response_model=PeriodCustomerRead)
def update_period_customer(
    link_id: int,
    payload: PeriodCustomerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pc = svc.update_period_customer(db, link_id, payload, current_user)
    enriched = svc.list_by_period(db, pc.contract_period_id)
    return next((r for r in enriched if r["id"] == pc.id), enriched[0])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period_customer(
    link_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc.delete_period_customer(db, link_id, current_user)

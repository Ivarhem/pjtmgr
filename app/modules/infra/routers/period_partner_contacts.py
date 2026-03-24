from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.period_partner_contact import (
    PeriodPartnerContactCreate,
    PeriodPartnerContactRead,
    PeriodPartnerContactUpdate,
)
from app.modules.infra.services import period_partner_contact_service as svc

router = APIRouter(
    prefix="/api/v1/period-partner-contacts",
    tags=["infra-period-partner-contacts"],
)


@router.get("", response_model=list[PeriodPartnerContactRead])
def list_period_partner_contacts(
    period_partner_id: int | None = None,
    contract_period_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PeriodPartnerContactRead]:
    if contract_period_id:
        return svc.list_by_period(db, contract_period_id)
    if period_partner_id:
        return svc.list_by_period_partner(db, period_partner_id)
    return []


@router.post(
    "", response_model=PeriodPartnerContactRead, status_code=status.HTTP_201_CREATED
)
def create_period_partner_contact(
    payload: PeriodPartnerContactCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ppc = svc.create_period_partner_contact(db, payload, current_user)
    enriched = svc.list_by_period_partner(db, ppc.period_partner_id)
    return next((r for r in enriched if r["id"] == ppc.id), enriched[0])


@router.patch("/{link_id}", response_model=PeriodPartnerContactRead)
def update_period_partner_contact(
    link_id: int,
    payload: PeriodPartnerContactUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ppc = svc.update_period_partner_contact(db, link_id, payload, current_user)
    enriched = svc.list_by_period_partner(db, ppc.period_partner_id)
    return next((r for r in enriched if r["id"] == ppc.id), enriched[0])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period_partner_contact(
    link_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc.delete_period_partner_contact(db, link_id, current_user)

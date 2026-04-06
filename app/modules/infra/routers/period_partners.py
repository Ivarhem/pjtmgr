from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.period_partner import (
    PeriodPartnerCreate,
    PeriodPartnerRead,
    PeriodPartnerUpdate,
)
from app.modules.infra.services import period_partner_service as svc

router = APIRouter(prefix="/api/v1/period-partners", tags=["infra-period-partners"])


@router.get("", response_model=list[PeriodPartnerRead])
def list_period_partners(
    contract_period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PeriodPartnerRead]:
    return svc.list_by_period(db, contract_period_id)


@router.post("", response_model=PeriodPartnerRead, status_code=status.HTTP_201_CREATED)
def create_period_partner(
    payload: PeriodPartnerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pp = svc.create_period_partner(db, payload, current_user)
    enriched = svc.list_by_period(db, pp.contract_period_id)
    return next((r for r in enriched if r["id"] == pp.id), enriched[0])


@router.patch("/{link_id}", response_model=PeriodPartnerRead)
def update_period_partner(
    link_id: int,
    payload: PeriodPartnerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pp = svc.update_period_partner(db, link_id, payload, current_user)
    enriched = svc.list_by_period(db, pp.contract_period_id)
    return next((r for r in enriched if r["id"] == pp.id), enriched[0])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period_partner(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc.delete_period_partner(db, link_id, current_user)

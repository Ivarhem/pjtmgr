from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.period_asset import (
    PeriodAssetCreate,
    PeriodAssetRead,
    PeriodAssetUpdate,
)
from app.modules.infra.services import period_asset_service as svc

router = APIRouter(prefix="/api/v1/period-assets", tags=["infra-period-assets"])


@router.get("", response_model=list[PeriodAssetRead])
def list_period_assets(
    contract_period_id: int | None = None,
    asset_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[PeriodAssetRead]:
    if contract_period_id:
        return svc.list_by_period(db, contract_period_id)
    if asset_id:
        return svc.list_by_asset(db, asset_id)
    return []


@router.post("", response_model=PeriodAssetRead, status_code=status.HTTP_201_CREATED)
def create_period_asset(
    payload: PeriodAssetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pa = svc.create_period_asset(db, payload, current_user)
    enriched = svc.list_by_period(db, pa.contract_period_id)
    return next((r for r in enriched if r["id"] == pa.id), enriched[0])


@router.patch("/{link_id}", response_model=PeriodAssetRead)
def update_period_asset(
    link_id: int,
    payload: PeriodAssetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pa = svc.update_period_asset(db, link_id, payload, current_user)
    enriched = svc.list_by_period(db, pa.contract_period_id)
    return next((r for r in enriched if r["id"] == pa.id), enriched[0])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period_asset(
    link_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc.delete_period_asset(db, link_id, current_user)

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.asset_relation import (
    AssetRelationCreate,
    AssetRelationRead,
    AssetRelationUpdate,
)
from app.modules.infra.services import asset_relation_service as svc

router = APIRouter(tags=["infra-asset-relations"])


@router.get("/api/v1/asset-relations", response_model=list[AssetRelationRead])
def list_asset_relations(
    customer_id: int | None = None,
    asset_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetRelationRead]:
    if asset_id is not None:
        return svc.list_by_asset(db, asset_id)
    if customer_id is not None:
        return svc.list_by_customer(db, customer_id)
    return []


@router.post("/api/v1/asset-relations", response_model=AssetRelationRead, status_code=status.HTTP_201_CREATED)
def create_asset_relation(
    payload: AssetRelationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rel = svc.create_asset_relation(db, payload, current_user)
    enriched = svc.list_by_asset(db, rel.src_asset_id)
    return next((r for r in enriched if r["id"] == rel.id), enriched[0])


@router.patch("/api/v1/asset-relations/{rel_id}", response_model=AssetRelationRead)
def update_asset_relation(
    rel_id: int,
    payload: AssetRelationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rel = svc.update_asset_relation(db, rel_id, payload, current_user)
    enriched = svc.list_by_asset(db, rel.src_asset_id)
    return next((r for r in enriched if r["id"] == rel.id), enriched[0])


@router.delete("/api/v1/asset-relations/{rel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset_relation(
    rel_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc.delete_asset_relation(db, rel_id, current_user)

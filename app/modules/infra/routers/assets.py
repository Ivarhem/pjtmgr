from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.asset import AssetBulkUpdateRequest, AssetCreate, AssetCurrentRoleUpdate, AssetRead, AssetUpdate
from app.modules.infra.services.asset_service import (
    bulk_update_assets,
    create_asset,
    delete_asset,
    enrich_assets_with_aliases,
    enrich_assets_with_period,
    get_asset,
    list_assets,
    update_asset_current_role,
    update_asset,
    enrich_asset_with_catalog_kind,
)


router = APIRouter(prefix="/api/v1/assets", tags=["infra-assets"])


@router.get("", response_model=list[AssetRead])
def list_assets_endpoint(
    partner_id: int,
    period_id: int | None = None,
    status: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetRead]:
    assets = list_assets(db, partner_id, period_id, status, q)
    return enrich_assets_with_aliases(db, assets)


@router.get("/inventory", response_model=list[AssetRead])
def list_assets_inventory(
    partner_id: int,
    period_id: int | None = None,
    status: str | None = None,
    q: str | None = None,
    layout_id: int | None = None,
    lang: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetRead]:
    """Partner-scoped asset inventory with period info enrichment."""
    assets = list_assets(db, partner_id, period_id, status, q)
    return enrich_assets_with_period(db, assets, layout_id=layout_id, lang=lang)


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset_endpoint(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    asset = create_asset(db, payload, current_user)
    return enrich_asset_with_catalog_kind(db, asset)


@router.patch("/bulk", response_model=list[AssetRead])
def bulk_update_assets_endpoint(
    payload: AssetBulkUpdateRequest,
    layout_id: int | None = None,
    lang: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetRead]:
    results = bulk_update_assets(db, payload.items, current_user)
    return [enrich_asset_with_catalog_kind(db, a, layout_id=layout_id, lang=lang) for a in results]


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    asset = get_asset(db, asset_id)
    return enrich_asset_with_catalog_kind(db, asset)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset_endpoint(
    asset_id: int,
    payload: AssetUpdate,
    layout_id: int | None = None,
    lang: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    asset = update_asset(db, asset_id, payload, current_user)
    return enrich_asset_with_catalog_kind(db, asset, layout_id=layout_id, lang=lang)


@router.patch("/{asset_id}/current-role", response_model=AssetRead)
def update_asset_current_role_endpoint(
    asset_id: int,
    payload: AssetCurrentRoleUpdate,
    layout_id: int | None = None,
    lang: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    asset = update_asset_current_role(db, asset_id, payload.asset_role_id, current_user)
    return enrich_asset_with_catalog_kind(db, asset, layout_id=layout_id, lang=lang)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_asset(db, asset_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.asset_alias import (
    AssetAliasCreate,
    AssetAliasRead,
    AssetAliasUpdate,
)
from app.modules.infra.services.asset_alias_service import (
    create_asset_alias,
    delete_asset_alias,
    list_asset_aliases,
    update_asset_alias,
)


router = APIRouter(tags=["infra-asset-aliases"])


@router.get(
    "/api/v1/assets/{asset_id}/aliases",
    response_model=list[AssetAliasRead],
)
def list_asset_aliases_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetAliasRead]:
    return list_asset_aliases(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/aliases",
    response_model=AssetAliasRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_alias_endpoint(
    asset_id: int,
    payload: AssetAliasCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetAliasRead:
    payload.asset_id = asset_id
    return create_asset_alias(db, payload, current_user)


@router.patch(
    "/api/v1/asset-aliases/{alias_id}",
    response_model=AssetAliasRead,
)
def update_asset_alias_endpoint(
    alias_id: int,
    payload: AssetAliasUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetAliasRead:
    return update_asset_alias(db, alias_id, payload, current_user)


@router.delete(
    "/api/v1/asset-aliases/{alias_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_alias_endpoint(
    alias_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_asset_alias(db, alias_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.schemas.asset_software import (
    AssetSoftwareCreate,
    AssetSoftwareRead,
    AssetSoftwareUpdate,
)
from app.modules.infra.services.asset_software_service import (
    create_asset_software,
    delete_asset_software,
    list_asset_software,
    update_asset_software,
)


router = APIRouter(tags=["infra-asset-software"])


@router.get(
    "/api/v1/assets/{asset_id}/software",
    response_model=list[AssetSoftwareRead],
)
def list_asset_software_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetSoftwareRead]:
    return list_asset_software(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/software",
    response_model=AssetSoftwareRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_software_endpoint(
    asset_id: int,
    payload: AssetSoftwareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetSoftwareRead:
    payload.asset_id = asset_id
    return create_asset_software(db, payload, current_user)


@router.patch(
    "/api/v1/asset-software/{software_id}",
    response_model=AssetSoftwareRead,
)
def update_asset_software_endpoint(
    software_id: int,
    payload: AssetSoftwareUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetSoftwareRead:
    return update_asset_software(db, software_id, payload, current_user)


@router.delete(
    "/api/v1/asset-software/{software_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_software_endpoint(
    software_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_asset_software(db, software_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

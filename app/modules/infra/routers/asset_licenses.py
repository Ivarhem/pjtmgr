from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.schemas.asset_license import (
    AssetLicenseCreate,
    AssetLicenseRead,
    AssetLicenseUpdate,
)
from app.modules.infra.services.asset_license_service import (
    create_asset_license,
    delete_asset_license,
    list_asset_licenses,
    update_asset_license,
)


router = APIRouter(tags=["infra-asset-licenses"])


@router.get(
    "/api/v1/assets/{asset_id}/licenses",
    response_model=list[AssetLicenseRead],
)
def list_asset_licenses_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetLicenseRead]:
    return list_asset_licenses(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/licenses",
    response_model=AssetLicenseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_license_endpoint(
    asset_id: int,
    payload: AssetLicenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetLicenseRead:
    payload.asset_id = asset_id
    return create_asset_license(db, payload, current_user)


@router.patch(
    "/api/v1/asset-licenses/{license_id}",
    response_model=AssetLicenseRead,
)
def update_asset_license_endpoint(
    license_id: int,
    payload: AssetLicenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetLicenseRead:
    return update_asset_license(db, license_id, payload, current_user)


@router.delete(
    "/api/v1/asset-licenses/{license_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_license_endpoint(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_asset_license(db, license_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

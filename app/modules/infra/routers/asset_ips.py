from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.asset_ip import AssetIPCreate, AssetIPRead, AssetIPUpdate
from app.modules.infra.services.network_service import (
    create_asset_ip,
    delete_asset_ip,
    get_asset_ip,
    list_asset_ips,
    list_customer_ips,
    update_asset_ip,
)


router = APIRouter(tags=["infra-asset-ips"])


@router.get(
    "/api/v1/assets/{asset_id}/ips",
    response_model=list[AssetIPRead],
)
def list_asset_ips_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetIPRead]:
    return list_asset_ips(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/ips",
    response_model=AssetIPRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_ip_endpoint(
    asset_id: int,
    payload: AssetIPCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetIPRead:
    payload.asset_id = asset_id
    return create_asset_ip(db, payload, current_user)


@router.get(
    "/api/v1/ip-inventory",
    response_model=list[AssetIPRead],
)
def list_customer_ips_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetIPRead]:
    return list_customer_ips(db, customer_id)


@router.get(
    "/api/v1/asset-ips/{ip_id}",
    response_model=AssetIPRead,
)
def get_asset_ip_endpoint(
    ip_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetIPRead:
    return get_asset_ip(db, ip_id)


@router.patch(
    "/api/v1/asset-ips/{ip_id}",
    response_model=AssetIPRead,
)
def update_asset_ip_endpoint(
    ip_id: int,
    payload: AssetIPUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetIPRead:
    return update_asset_ip(db, ip_id, payload, current_user)


@router.delete(
    "/api/v1/asset-ips/{ip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_ip_endpoint(
    ip_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_asset_ip(db, ip_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

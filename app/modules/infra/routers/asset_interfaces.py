from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.schemas.asset_interface import (
    AssetInterfaceBulkCreate,
    AssetInterfaceCreate,
    AssetInterfaceRead,
    AssetInterfaceUpdate,
)
from app.modules.infra.services.asset_interface_service import (
    create_interface,
    delete_interface,
    generate_interfaces_from_catalog,
    get_interface,
    list_interfaces,
    set_lag_members,
    update_interface,
)

router = APIRouter(tags=["infra-asset-interfaces"])


@router.get(
    "/api/v1/assets/{asset_id}/interfaces",
    response_model=list[AssetInterfaceRead],
)
def list_interfaces_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetInterfaceRead]:
    return list_interfaces(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/interfaces",
    response_model=AssetInterfaceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_interface_endpoint(
    asset_id: int,
    payload: AssetInterfaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetInterfaceRead:
    payload.asset_id = asset_id
    return create_interface(db, payload, current_user)


@router.post(
    "/api/v1/assets/{asset_id}/interfaces/generate",
    response_model=list[AssetInterfaceRead],
    status_code=status.HTTP_201_CREATED,
)
def generate_interfaces_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetInterfaceRead]:
    return generate_interfaces_from_catalog(db, asset_id, current_user)


@router.get(
    "/api/v1/asset-interfaces/{interface_id}",
    response_model=AssetInterfaceRead,
)
def get_interface_endpoint(
    interface_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetInterfaceRead:
    return get_interface(db, interface_id)


@router.patch(
    "/api/v1/asset-interfaces/{interface_id}",
    response_model=AssetInterfaceRead,
)
def update_interface_endpoint(
    interface_id: int,
    payload: AssetInterfaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetInterfaceRead:
    return update_interface(db, interface_id, payload, current_user)


@router.delete(
    "/api/v1/asset-interfaces/{interface_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_interface_endpoint(
    interface_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_interface(db, interface_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api/v1/asset-interfaces/{lag_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
)
def set_lag_members_endpoint(
    lag_id: int,
    member_ids: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    set_lag_members(db, lag_id, member_ids, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

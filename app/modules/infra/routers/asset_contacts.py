from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.asset_contact import (
    AssetContactCreate,
    AssetContactRead,
    AssetContactUpdate,
)
from app.modules.infra.services.asset_service import (
    create_asset_contact,
    delete_asset_contact,
    list_asset_contacts,
    update_asset_contact,
)


router = APIRouter(tags=["infra-asset-contacts"])


@router.get(
    "/api/v1/assets/{asset_id}/contacts",
    response_model=list[AssetContactRead],
)
def list_asset_contacts_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[AssetContactRead]:
    return list_asset_contacts(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/contacts",
    response_model=AssetContactRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_contact_endpoint(
    asset_id: int,
    payload: AssetContactCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetContactRead:
    payload.asset_id = asset_id
    return create_asset_contact(db, payload, current_user)


@router.patch(
    "/api/v1/asset-contacts/{asset_contact_id}",
    response_model=AssetContactRead,
)
def update_asset_contact_endpoint(
    asset_contact_id: int,
    payload: AssetContactUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> AssetContactRead:
    return update_asset_contact(db, asset_contact_id, payload, current_user)


@router.delete(
    "/api/v1/asset-contacts/{asset_contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_contact_endpoint(
    asset_contact_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_asset_contact(db, asset_contact_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

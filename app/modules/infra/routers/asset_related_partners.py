from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.asset_related_partner import (
    AssetRelatedPartnerCreate,
    AssetRelatedPartnerRead,
    AssetRelatedPartnerUpdate,
)
from app.modules.infra.services.asset_related_partner_service import (
    create_asset_related_partner,
    delete_asset_related_partner,
    list_asset_related_partners,
    update_asset_related_partner,
)


router = APIRouter(tags=["infra-asset-related-partners"])


@router.get(
    "/api/v1/assets/{asset_id}/related-partners",
    response_model=list[AssetRelatedPartnerRead],
)
def list_asset_related_partners_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetRelatedPartnerRead]:
    return list_asset_related_partners(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/related-partners",
    response_model=AssetRelatedPartnerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_related_partner_endpoint(
    asset_id: int,
    payload: AssetRelatedPartnerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRelatedPartnerRead:
    payload.asset_id = asset_id
    return create_asset_related_partner(db, payload, current_user)


@router.patch(
    "/api/v1/asset-related-partners/{asset_related_partner_id}",
    response_model=AssetRelatedPartnerRead,
)
def update_asset_related_partner_endpoint(
    asset_related_partner_id: int,
    payload: AssetRelatedPartnerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRelatedPartnerRead:
    return update_asset_related_partner(db, asset_related_partner_id, payload, current_user)


@router.delete(
    "/api/v1/asset-related-partners/{asset_related_partner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_related_partner_endpoint(
    asset_related_partner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_asset_related_partner(db, asset_related_partner_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

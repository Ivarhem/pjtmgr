from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.asset_event import AssetEventCreate, AssetEventRead
from app.modules.infra.services.asset_event_service import (
    create_asset_event,
    list_asset_events,
)


router = APIRouter(tags=["infra-asset-events"])


@router.get(
    "/api/v1/assets/{asset_id}/events",
    response_model=list[AssetEventRead],
)
def list_asset_events_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetEventRead]:
    return list_asset_events(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/events",
    response_model=AssetEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_event_endpoint(
    asset_id: int,
    payload: AssetEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetEventRead:
    return create_asset_event(db, asset_id, payload, current_user)

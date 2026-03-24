"""AssetTypeCode CRUD 라우터."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.common.schemas.asset_type_code import (
    AssetTypeCodeCreate,
    AssetTypeCodeRead,
    AssetTypeCodeUpdate,
)
from app.modules.common.services import asset_type_code as svc

router = APIRouter(prefix="/api/v1/asset-type-codes", tags=["asset-type-codes"])


@router.get("", response_model=list[AssetTypeCodeRead])
def list_asset_type_codes(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[AssetTypeCodeRead]:
    return svc.list_asset_type_codes(db, active_only=active_only)


@router.post("", response_model=AssetTypeCodeRead, status_code=201)
def create_asset_type_code(
    data: AssetTypeCodeCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AssetTypeCodeRead:
    return svc.create_asset_type_code(db, data.type_key, data.code, data.label, data.sort_order)


@router.patch("/{type_key}", response_model=AssetTypeCodeRead)
def update_asset_type_code(
    type_key: str,
    data: AssetTypeCodeUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AssetTypeCodeRead:
    return svc.update_asset_type_code(db, type_key, updates=data.model_dump(exclude_unset=True))


@router.delete("/{type_key}", status_code=204)
def delete_asset_type_code(
    type_key: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_asset_type_code(db, type_key)

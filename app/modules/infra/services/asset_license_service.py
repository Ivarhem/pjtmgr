from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.modules.common.models.user import User
from app.core.exceptions import (
    NotFoundError,
    PermissionDeniedError,
)
from app.modules.common.services import audit
from app.modules.infra.models.asset_license import AssetLicense
from app.modules.infra.schemas.asset_license import (
    AssetLicenseCreate,
    AssetLicenseUpdate,
)


def list_asset_licenses(db: Session, asset_id: int) -> list[AssetLicense]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetLicense)
            .where(AssetLicense.asset_id == asset_id)
            .order_by(AssetLicense.id.asc())
        )
    )


def get_asset_license(db: Session, license_id: int) -> AssetLicense:
    lic = db.get(AssetLicense, license_id)
    if lic is None:
        raise NotFoundError("Asset license not found")
    return lic


def create_asset_license(
    db: Session, payload: AssetLicenseCreate, current_user: User
) -> AssetLicense:
    _require_inventory_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)

    lic = AssetLicense(**payload.model_dump())
    db.add(lic)
    audit.log(
        db,
        user_id=current_user.id,
        action="create",
        entity_type="asset_license",
        entity_id=None,
        summary=f"자산 라이선스 등록: {lic.license_type}",
        module="infra",
    )
    db.commit()
    db.refresh(lic)
    return lic


def update_asset_license(
    db: Session, license_id: int, payload: AssetLicenseUpdate, current_user: User
) -> AssetLicense:
    _require_inventory_edit(current_user)
    lic = get_asset_license(db, license_id)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        setattr(lic, field, value)

    audit.log(
        db,
        user_id=current_user.id,
        action="update",
        entity_type="asset_license",
        entity_id=lic.id,
        summary=f"자산 라이선스 수정: {lic.license_type}",
        module="infra",
    )
    db.commit()
    db.refresh(lic)
    return lic


def delete_asset_license(db: Session, license_id: int, current_user: User) -> None:
    _require_inventory_edit(current_user)
    lic = get_asset_license(db, license_id)
    audit.log(
        db,
        user_id=current_user.id,
        action="delete",
        entity_type="asset_license",
        entity_id=lic.id,
        summary=f"자산 라이선스 삭제: {lic.license_type}",
        module="infra",
    )
    db.delete(lic)
    db.commit()


# ── Private helpers ──


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    from app.modules.infra.models.asset import Asset

    if db.get(Asset, asset_id) is None:
        raise NotFoundError("Asset not found")


def _require_inventory_edit(current_user: User) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("Inventory edit permission required")

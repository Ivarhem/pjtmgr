from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_alias import AssetAlias
from app.modules.infra.schemas.asset_alias import AssetAliasCreate, AssetAliasUpdate


def _require_edit(current_user: User) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("편집 권한이 없습니다")


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    if not db.get(Asset, asset_id):
        raise NotFoundError("자산을 찾을 수 없습니다")


def _check_alias_unique(db: Session, alias_name: str, exclude_id: int | None = None) -> None:
    stmt = select(AssetAlias).where(AssetAlias.alias_name == alias_name)
    if exclude_id:
        stmt = stmt.where(AssetAlias.id != exclude_id)
    if db.scalars(stmt).first():
        raise DuplicateError(f"별칭 '{alias_name}'이 이미 사용 중입니다")


def list_asset_aliases(db: Session, asset_id: int) -> list[AssetAlias]:
    _ensure_asset_exists(db, asset_id)
    return list(db.scalars(
        select(AssetAlias).where(AssetAlias.asset_id == asset_id)
        .order_by(AssetAlias.is_primary.desc(), AssetAlias.alias_name)
    ))


def create_asset_alias(db: Session, payload: AssetAliasCreate, current_user: User) -> AssetAlias:
    _require_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)
    _check_alias_unique(db, payload.alias_name)
    alias = AssetAlias(**payload.model_dump())
    db.add(alias)
    audit.log(db, user_id=current_user.id, action="create", module="infra",
              entity_type="asset_alias", entity_id=None,
              summary=f"별칭 생성: {payload.alias_name} (asset={payload.asset_id})")
    db.commit()
    db.refresh(alias)
    return alias


def update_asset_alias(db: Session, alias_id: int, payload: AssetAliasUpdate, current_user: User) -> AssetAlias:
    _require_edit(current_user)
    alias = db.get(AssetAlias, alias_id)
    if not alias:
        raise NotFoundError("별칭을 찾을 수 없습니다")
    data = payload.model_dump(exclude_unset=True)
    if "alias_name" in data:
        _check_alias_unique(db, data["alias_name"], exclude_id=alias_id)
    for k, v in data.items():
        setattr(alias, k, v)
    audit.log(db, user_id=current_user.id, action="update", module="infra",
              entity_type="asset_alias", entity_id=alias_id,
              summary=f"별칭 수정: {alias.alias_name}")
    db.commit()
    db.refresh(alias)
    return alias


def delete_asset_alias(db: Session, alias_id: int, current_user: User) -> None:
    _require_edit(current_user)
    alias = db.get(AssetAlias, alias_id)
    if not alias:
        raise NotFoundError("별칭을 찾을 수 없습니다")
    audit.log(db, user_id=current_user.id, action="delete", module="infra",
              entity_type="asset_alias", entity_id=alias_id,
              summary=f"별칭 삭제: {alias.alias_name}")
    db.delete(alias)
    db.commit()

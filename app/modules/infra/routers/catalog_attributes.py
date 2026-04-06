from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.modules.common.models.user import User
from app.core.database import get_db
from app.modules.infra.schemas.catalog_attribute import (
    CatalogAttributeCreate,
    CatalogAttributeRead,
    CatalogAttributeUpdate,
)
from app.modules.infra.schemas.catalog_attribute_option import (
    CatalogAttributeOptionCreate,
    CatalogAttributeOptionRead,
    CatalogAttributeOptionUpdate,
)
from app.modules.infra.services.catalog_attribute_service import (
    create_attribute,
    create_attribute_option,
    delete_attribute,
    delete_attribute_option,
    list_attribute_options,
    list_attributes,
    update_attribute,
    update_attribute_option,
)


router = APIRouter(prefix="/api/v1/catalog-attributes", tags=["infra-catalog-attributes"])


@router.get("", response_model=list[CatalogAttributeRead])
def list_catalog_attributes(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CatalogAttributeRead]:
    return list_attributes(db, active_only=active_only)


@router.post("", response_model=CatalogAttributeRead, status_code=status.HTTP_201_CREATED)
def create_catalog_attribute(
    payload: CatalogAttributeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogAttributeRead:
    return create_attribute(db, payload, current_user)


@router.patch("/{attribute_id}", response_model=CatalogAttributeRead)
def update_catalog_attribute(
    attribute_id: int,
    payload: CatalogAttributeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogAttributeRead:
    return update_attribute(db, attribute_id, payload, current_user)


@router.delete("/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_attribute(
    attribute_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_attribute(db, attribute_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{attribute_id}/options", response_model=list[CatalogAttributeOptionRead])
def list_catalog_attribute_options(
    attribute_id: int,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CatalogAttributeOptionRead]:
    return list_attribute_options(db, attribute_id, active_only=active_only)


@router.post("/{attribute_id}/options", response_model=CatalogAttributeOptionRead, status_code=status.HTTP_201_CREATED)
def create_catalog_attribute_option(
    attribute_id: int,
    payload: CatalogAttributeOptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogAttributeOptionRead:
    return create_attribute_option(db, attribute_id, payload, current_user)


@router.patch("/options/{option_id}", response_model=CatalogAttributeOptionRead)
def update_catalog_attribute_option(
    option_id: int,
    payload: CatalogAttributeOptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogAttributeOptionRead:
    return update_attribute_option(db, option_id, payload, current_user)


@router.delete("/options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_attribute_option(
    option_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_attribute_option(db, option_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

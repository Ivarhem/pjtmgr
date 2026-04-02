from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.schemas.catalog_attribute_option_alias import (
    CatalogAttributeOptionAliasCreate,
    CatalogAttributeOptionAliasRead,
    CatalogAttributeOptionAliasUpdate,
)
from app.modules.infra.schemas.catalog_vendor_management import (
    CatalogVendorBulkUpsertRequest,
    CatalogVendorBulkUpsertResponse,
)
from app.modules.infra.services.catalog_alias_service import (
    bulk_upsert_vendor_aliases,
    create_attribute_option_alias,
    delete_attribute_option_alias,
    update_attribute_option_alias,
)
from app.modules.infra.services.catalog_integrity_service import (
    get_catalog_attribute_alias_integrity,
    list_catalog_attribute_alias_integrity,
    list_catalog_vendor_integrity,
    list_similar_catalog_products,
)


router = APIRouter(prefix="/api/v1/catalog-integrity", tags=["infra-catalog-integrity"])


@router.get("/vendors")
def list_catalog_integrity_vendors(
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return list_catalog_vendor_integrity(db, q=q)


@router.post("/vendors/bulk-upsert", response_model=CatalogVendorBulkUpsertResponse)
def bulk_upsert_catalog_integrity_vendors(
    payload: CatalogVendorBulkUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogVendorBulkUpsertResponse:
    return CatalogVendorBulkUpsertResponse(**bulk_upsert_vendor_aliases(db, payload.rows, current_user))


@router.get("/similar-products")
def list_catalog_integrity_similar_products(
    q: str | None = None,
    min_score: int = 75,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    return list_similar_catalog_products(db, q=q, min_score=min_score, limit=limit)


@router.get("/attribute-aliases", response_model=list[CatalogAttributeOptionAliasRead])
def list_catalog_integrity_attribute_aliases(
    attribute_key: str | None = None,
    q: str | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CatalogAttributeOptionAliasRead]:
    return list_catalog_attribute_alias_integrity(db, attribute_key=attribute_key, q=q, active_only=active_only)


@router.get("/attribute-aliases/{alias_id}", response_model=CatalogAttributeOptionAliasRead)
def get_catalog_integrity_attribute_alias(
    alias_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogAttributeOptionAliasRead:
    return get_catalog_attribute_alias_integrity(db, alias_id)


@router.post("/attribute-aliases", response_model=CatalogAttributeOptionAliasRead, status_code=status.HTTP_201_CREATED)
def create_catalog_integrity_attribute_alias(
    payload: CatalogAttributeOptionAliasCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogAttributeOptionAliasRead:
    return create_attribute_option_alias(db, payload, current_user)


@router.patch("/attribute-aliases/{alias_id}", response_model=CatalogAttributeOptionAliasRead)
def update_catalog_integrity_attribute_alias(
    alias_id: int,
    payload: CatalogAttributeOptionAliasUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogAttributeOptionAliasRead:
    return update_attribute_option_alias(db, alias_id, payload, current_user)


@router.delete("/attribute-aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_integrity_attribute_alias(
    alias_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_attribute_option_alias(db, alias_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.schemas.product_catalog import (
    ProductCatalogBulkUpsertRequest,
    ProductCatalogBulkUpsertResponse,
    ProductCatalogCreate,
    ProductCatalogDetail,
    ProductCatalogRead,
    ProductCatalogUpdate,
)
from app.modules.infra.schemas.catalog_similarity import (
    CatalogSimilarityCheckRequest,
    CatalogSimilarityCheckResponse,
    ProductMergeRequest,
    ProductMergeResponse,
    ProductDismissRequest,
    ProductRestoreRequest,
)
from app.modules.infra.services.catalog_merge_service import (
    merge_products,
    dismiss_similarity,
    restore_similarity,
)
from app.modules.infra.schemas.hardware_spec import (
    HardwareSpecCreate,
    HardwareSpecRead,
)
from app.modules.infra.schemas.software_spec import (
    SoftwareSpecCreate,
    SoftwareSpecRead,
)
from app.modules.infra.schemas.model_spec import (
    ModelSpecCreate,
    ModelSpecRead,
)
from app.modules.infra.schemas.generic_catalog_profile import (
    GenericCatalogProfileCreate,
    GenericCatalogProfileRead,
)
from app.modules.infra.schemas.hardware_interface import (
    HardwareInterfaceCreate,
    HardwareInterfaceRead,
    HardwareInterfaceUpdate,
)
from app.modules.infra.services.product_catalog_service import (
    bulk_upsert_products,
    create_interface,
    create_product,
    delete_interface,
    delete_product,
    get_product_detail,
    list_interfaces,
    list_products,
    upsert_generic_profile,
    upsert_model_spec,
    upsert_software_spec,
    update_interface,
    update_product,
    upsert_spec,
)
from app.modules.infra.services.catalog_similarity_service import find_similar_products


router = APIRouter(prefix="/api/v1/product-catalog", tags=["infra-product-catalog"])


# ── Product CRUD ──


@router.get("", response_model=list[ProductCatalogRead])
def list_products_endpoint(
    vendor: str | None = None,
    product_type: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProductCatalogRead]:
    return list_products(db, vendor, product_type, q)


@router.post(
    "", response_model=ProductCatalogRead, status_code=status.HTTP_201_CREATED
)
def create_product_endpoint(
    payload: ProductCatalogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogRead:
    return create_product(db, payload, current_user)


@router.post("/bulk-upsert", response_model=ProductCatalogBulkUpsertResponse)
def bulk_upsert_products_endpoint(
    payload: ProductCatalogBulkUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogBulkUpsertResponse:
    return ProductCatalogBulkUpsertResponse(**bulk_upsert_products(db, payload.rows, current_user))


@router.post("/similarity-check", response_model=CatalogSimilarityCheckResponse)
def check_product_similarity_endpoint(
    payload: CatalogSimilarityCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CatalogSimilarityCheckResponse:
    return CatalogSimilarityCheckResponse(**find_similar_products(
        db,
        vendor=payload.vendor,
        name=payload.name,
        exclude_product_id=payload.exclude_product_id,
        include_dismissed=payload.include_dismissed,
    ))


@router.post("/merge", response_model=ProductMergeResponse)
def merge_products_endpoint(
    payload: ProductMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductMergeResponse:
    result = merge_products(
        db,
        source_id=payload.source_id,
        target_id=payload.target_id,
        current_user=current_user,
    )
    return ProductMergeResponse(**result)


@router.post("/similarity-dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_similarity_endpoint(
    payload: ProductDismissRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    dismiss_similarity(db, product_id_a=payload.product_id_a, product_id_b=payload.product_id_b)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/similarity-restore", status_code=status.HTTP_204_NO_CONTENT)
def restore_similarity_endpoint(
    payload: ProductRestoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    restore_similarity(db, product_id_a=payload.product_id_a, product_id_b=payload.product_id_b)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{product_id}", response_model=ProductCatalogDetail)
def get_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogDetail:
    return get_product_detail(db, product_id)


@router.patch("/{product_id}", response_model=ProductCatalogRead)
def update_product_endpoint(
    product_id: int,
    payload: ProductCatalogUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogRead:
    return update_product(db, product_id, payload, current_user)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_product(db, product_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── HardwareSpec (1:1) ──


@router.post("/{product_id}/spec", response_model=HardwareSpecRead)
def upsert_spec_endpoint(
    product_id: int,
    payload: HardwareSpecCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HardwareSpecRead:
    return upsert_spec(db, product_id, payload, current_user)


@router.post("/{product_id}/software-spec", response_model=SoftwareSpecRead)
def upsert_software_spec_endpoint(
    product_id: int,
    payload: SoftwareSpecCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SoftwareSpecRead:
    return upsert_software_spec(db, product_id, payload, current_user)


@router.post("/{product_id}/model-spec", response_model=ModelSpecRead)
def upsert_model_spec_endpoint(
    product_id: int,
    payload: ModelSpecCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ModelSpecRead:
    return upsert_model_spec(db, product_id, payload, current_user)


@router.post("/{product_id}/generic-profile", response_model=GenericCatalogProfileRead)
def upsert_generic_profile_endpoint(
    product_id: int,
    payload: GenericCatalogProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenericCatalogProfileRead:
    return upsert_generic_profile(db, product_id, payload, current_user)


# ── HardwareInterface (1:N) ──


@router.get("/{product_id}/interfaces", response_model=list[HardwareInterfaceRead])
def list_interfaces_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HardwareInterfaceRead]:
    return list_interfaces(db, product_id)


@router.post(
    "/{product_id}/interfaces",
    response_model=HardwareInterfaceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_interface_endpoint(
    product_id: int,
    payload: HardwareInterfaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HardwareInterfaceRead:
    return create_interface(db, product_id, payload, current_user)


@router.patch(
    "/{product_id}/interfaces/{interface_id}",
    response_model=HardwareInterfaceRead,
)
def update_interface_endpoint(
    product_id: int,
    interface_id: int,
    payload: HardwareInterfaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HardwareInterfaceRead:
    return update_interface(db, product_id, interface_id, payload, current_user)


@router.delete(
    "/{product_id}/interfaces/{interface_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_interface_endpoint(
    product_id: int,
    interface_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_interface(db, product_id, interface_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

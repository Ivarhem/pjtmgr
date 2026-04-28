from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.auth.authorization import get_permissions
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.schemas.product_catalog import (
    ProductCatalogBulkActionResponse,
    ProductCatalogBulkUpsertRequest,
    ProductCatalogBulkUpsertResponse,
    ProductCatalogBulkVerificationStatusUpdate,
    ProductCatalogCreate,
    ProductCatalogDetail,
    ProductCatalogRead,
    ProductCatalogUpdate,
    ProductCatalogVerificationStatusUpdate,
)
from app.modules.infra.schemas.catalog_similarity import (
    CatalogSimilarityCheckRequest,
    CatalogSimilarityCheckResponse,
    ProductMergeRequest,
    ProductMergeResponse,
    ProductDismissRequest,
    ProductRestoreRequest,
)
from app.modules.infra.schemas.product_catalog_research import (
    ProductCatalogBatchResearchRequest,
    ProductCatalogBatchResearchResponse,
    ProductCatalogResearchRequest,
    ProductCatalogResearchResponse,
    ProductCatalogSkuExpansionApplyRequest,
    ProductCatalogSkuExpansionApplyResponse,
    ProductCatalogSkuExpansionPreviewResponse,
)
from app.modules.infra.services.catalog_merge_service import (
    merge_products,
    dismiss_similarity,
    restore_similarity,
)
from app.modules.infra.services.catalog_research_service import (
    apply_product_sku_expansion,
    batch_research_catalog_products,
    preview_product_sku_expansion,
    research_catalog_product,
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
from app.modules.common.services.user_preference import get_preference
from app.modules.infra.services.catalog_attribute_service import list_attribute_options, list_attributes
from app.modules.infra.services.classification_layout_service import get_layout_detail, list_layouts
from app.modules.infra.services.product_catalog_service import (
    bulk_set_product_verification_status,
    bulk_upsert_products,
    create_interface,
    create_product,
    delete_interface,
    delete_product,
    get_product_detail,
    list_interfaces,
    list_products,
    mark_product_verified,
    set_product_verification_status,
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


@router.get("/bootstrap")
def catalog_bootstrap_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """제품 카탈로그 초기 화면에 필요한 기준정보/목록을 한 번에 반환한다."""
    attr_defs = list_attributes(db, active_only=False)
    layouts = list_layouts(db, scope_type="global", active_only=True)
    preferred_raw = get_preference(db, current_user.id, "catalog.layout_preset_id")
    preferred_id = int(preferred_raw) if str(preferred_raw or "").isdigit() else None
    target_layout = (
        next((item for item in layouts if preferred_id and item.id == preferred_id), None)
        or next((item for item in layouts if item.is_default), None)
        or (layouts[0] if layouts else None)
    )
    layout_detail = get_layout_detail(db, target_layout.id) if target_layout else None

    active_options_by_attribute_key = {}
    for attr in attr_defs:
        active_options_by_attribute_key[attr.attribute_key] = list_attribute_options(db, attr.id, active_only=True)

    return jsonable_encoder({
        "me": {
            "id": current_user.id,
            "name": current_user.name,
            "permissions": get_permissions(current_user),
        },
        "label_lang": get_preference(db, current_user.id, "catalog.label_lang") or "ko",
        "attributes": attr_defs,
        "layouts": layouts,
        "layout_detail": layout_detail,
        "active_options_by_attribute_key": active_options_by_attribute_key,
        "products": list_products(db, None, None, None),
    })


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


@router.patch("/bulk/verification-status", response_model=ProductCatalogBulkActionResponse)
def bulk_update_verification_status_endpoint(
    payload: ProductCatalogBulkVerificationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogBulkActionResponse:
    return ProductCatalogBulkActionResponse(**bulk_set_product_verification_status(
        db, payload.product_ids, payload.verification_status, current_user
    ))


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

@router.post("/{product_id}/research", response_model=ProductCatalogResearchResponse)
def research_product_endpoint(
    product_id: int,
    payload: ProductCatalogResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogResearchResponse:
    return ProductCatalogResearchResponse(**research_catalog_product(
        db,
        product_id=product_id,
        current_user=current_user,
        fill_only=payload.fill_only,
        force=payload.force,
    ))


@router.post("/research/batch", response_model=ProductCatalogBatchResearchResponse)
def batch_research_products_endpoint(
    payload: ProductCatalogBatchResearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogBatchResearchResponse:
    return ProductCatalogBatchResearchResponse(**batch_research_catalog_products(
        db,
        current_user=current_user,
        limit=payload.limit,
        fill_only=payload.fill_only,
        force=payload.force,
        include_pending_review=payload.include_pending_review,
    ))


@router.get("/{product_id}/sku-expansion-preview", response_model=ProductCatalogSkuExpansionPreviewResponse)
def preview_product_sku_expansion_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogSkuExpansionPreviewResponse:
    return ProductCatalogSkuExpansionPreviewResponse(**preview_product_sku_expansion(db, product_id))


@router.post("/{product_id}/sku-expansion-apply", response_model=ProductCatalogSkuExpansionApplyResponse)
def apply_product_sku_expansion_endpoint(
    product_id: int,
    payload: ProductCatalogSkuExpansionApplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogSkuExpansionApplyResponse:
    return ProductCatalogSkuExpansionApplyResponse(**apply_product_sku_expansion(
        db,
        product_id,
        current_user,
        selected_names=payload.selected_names,
        delete_family_after_expand=payload.delete_family,
    ))


@router.post("/{product_id}/mark-verified", response_model=ProductCatalogRead)
def mark_product_verified_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogRead:
    return mark_product_verified(db, product_id, current_user)


@router.patch("/{product_id}/verification-status", response_model=ProductCatalogRead)
def set_product_verification_status_endpoint(
    product_id: int,
    payload: ProductCatalogVerificationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductCatalogRead:
    return set_product_verification_status(db, product_id, payload.verification_status, current_user)


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

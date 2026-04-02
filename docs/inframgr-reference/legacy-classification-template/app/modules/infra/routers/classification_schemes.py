from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.classification_scheme import (
    ClassificationSchemeCopyRequest,
    ClassificationSchemeCreate,
    ClassificationSchemeInitRequest,
    ClassificationSchemeRead,
    ClassificationSchemeUpdate,
)
from app.modules.infra.services.classification_service import (
    copy_classification_scheme,
    create_classification_scheme,
    delete_classification_scheme,
    initialize_project_classification_scheme,
    list_classification_scheme_sources,
    list_classification_schemes,
    update_classification_scheme,
)

router = APIRouter(tags=["infra-classification-schemes"])


@router.get("/api/v1/classification-schemes", response_model=list[ClassificationSchemeRead])
def list_classification_schemes_endpoint(
    scope_type: str | None = None,
    project_id: int | None = None,
    partner_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ClassificationSchemeRead]:
    return list_classification_schemes(db, scope_type=scope_type, project_id=project_id, partner_id=partner_id)


@router.get("/api/v1/classification-scheme-sources")
def list_classification_scheme_sources_endpoint(
    partner_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    return list_classification_scheme_sources(db, partner_id=partner_id)


@router.post("/api/v1/classification-schemes", response_model=ClassificationSchemeRead, status_code=status.HTTP_201_CREATED)
def create_classification_scheme_endpoint(
    payload: ClassificationSchemeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ClassificationSchemeRead:
    return create_classification_scheme(db, payload, current_user)


@router.patch("/api/v1/classification-schemes/{scheme_id}", response_model=ClassificationSchemeRead)
def update_classification_scheme_endpoint(
    scheme_id: int,
    payload: ClassificationSchemeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ClassificationSchemeRead:
    return update_classification_scheme(db, scheme_id, payload, current_user)


@router.post("/api/v1/classification-schemes/{scheme_id}/copy", response_model=ClassificationSchemeRead, status_code=status.HTTP_201_CREATED)
def copy_classification_scheme_endpoint(
    scheme_id: int,
    payload: ClassificationSchemeCopyRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ClassificationSchemeRead:
    return copy_classification_scheme(db, scheme_id, payload, current_user)


@router.post("/api/v1/projects/{project_id}/classification-scheme/init", response_model=ClassificationSchemeRead, status_code=status.HTTP_201_CREATED)
def initialize_project_classification_scheme_endpoint(
    project_id: int,
    payload: ClassificationSchemeInitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ClassificationSchemeRead:
    return initialize_project_classification_scheme(
        db,
        project_id=project_id,
        payload=payload,
        current_user=current_user,
    )


@router.delete("/api/v1/classification-schemes/{scheme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classification_scheme_endpoint(
    scheme_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_classification_scheme(db, scheme_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

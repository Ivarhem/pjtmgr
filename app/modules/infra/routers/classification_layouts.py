from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.classification_layout import (
    ClassificationLayoutCreate,
    ClassificationLayoutRead,
    ClassificationLayoutUpdate,
)
from app.modules.infra.schemas.project_classification_layout import (
    ProjectClassificationLayoutRead,
    ProjectClassificationLayoutUpdate,
)
from app.modules.infra.services.classification_layout_service import (
    assign_project_layout,
    create_layout,
    delete_layout,
    get_layout_detail,
    get_project_layout,
    list_layouts,
    update_layout,
)


router = APIRouter(prefix="/api/v1/classification-layouts", tags=["infra-classification-layouts"])


@router.get("", response_model=list[ClassificationLayoutRead])
def list_classification_layouts(
    scope_type: str | None = None,
    project_id: int | None = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ClassificationLayoutRead]:
    return list_layouts(db, scope_type=scope_type, project_id=project_id, active_only=active_only)


@router.get("/{layout_id}")
def get_classification_layout(
    layout_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    return get_layout_detail(db, layout_id)


@router.post("", response_model=ClassificationLayoutRead, status_code=status.HTTP_201_CREATED)
def create_classification_layout(
    payload: ClassificationLayoutCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ClassificationLayoutRead:
    return create_layout(db, payload, current_user)


@router.patch("/{layout_id}", response_model=ClassificationLayoutRead)
def update_classification_layout(
    layout_id: int,
    payload: ClassificationLayoutUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ClassificationLayoutRead:
    return update_layout(db, layout_id, payload, current_user)


@router.delete("/{layout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classification_layout(
    layout_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_layout(db, layout_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/projects/{project_id}", response_model=ProjectClassificationLayoutRead | None)
def get_project_classification_layout(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectClassificationLayoutRead | None:
    layout = get_project_layout(db, project_id)
    if layout is None:
        return None
    return ProjectClassificationLayoutRead(
        project_id=project_id,
        layout_id=layout.id,
        layout_name=layout.name,
    )


@router.put("/projects/{project_id}", response_model=ProjectClassificationLayoutRead)
def put_project_classification_layout(
    project_id: int,
    payload: ProjectClassificationLayoutUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectClassificationLayoutRead:
    assign_project_layout(db, project_id, payload.layout_id, current_user)
    detail = get_layout_detail(db, payload.layout_id)
    return ProjectClassificationLayoutRead(
        project_id=project_id,
        layout_id=payload.layout_id,
        layout_name=detail["name"],
    )

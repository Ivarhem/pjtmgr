from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.classification_node import (
    ClassificationNodeCreate,
    ClassificationNodeRead,
    ClassificationNodeUpdate,
)
from app.modules.infra.services.classification_service import (
    create_classification_node,
    delete_classification_node,
    list_classification_nodes,
    update_classification_node,
)

router = APIRouter(tags=["infra-classification-nodes"])


@router.get("/api/v1/classification-schemes/{scheme_id}/nodes", response_model=list[ClassificationNodeRead])
def list_classification_nodes_endpoint(
    scheme_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ClassificationNodeRead]:
    return list_classification_nodes(db, scheme_id)


@router.post("/api/v1/classification-schemes/{scheme_id}/nodes", response_model=ClassificationNodeRead, status_code=status.HTTP_201_CREATED)
def create_classification_node_endpoint(
    scheme_id: int,
    payload: ClassificationNodeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ClassificationNodeRead:
    return create_classification_node(db, scheme_id, payload, current_user)


@router.patch("/api/v1/classification-nodes/{node_id}", response_model=ClassificationNodeRead)
def update_classification_node_endpoint(
    node_id: int,
    payload: ClassificationNodeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ClassificationNodeRead:
    return update_classification_node(db, node_id, payload, current_user)


@router.delete("/api/v1/classification-nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classification_node_endpoint(
    node_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_classification_node(db, node_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

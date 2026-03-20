from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.modules.infra.services.project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)


router = APIRouter(prefix="/api/v1/projects", tags=["infra-projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects_endpoint(
    customer_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectRead]:
    return list_projects(db, customer_id)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectRead:
    return create_project(db, payload, current_user)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectRead:
    return get_project(db, project_id)


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project_endpoint(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ProjectRead:
    return update_project(db, project_id, payload, current_user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_endpoint(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    delete_project(db, project_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

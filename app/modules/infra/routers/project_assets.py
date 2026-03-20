from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.project_asset import (
    ProjectAssetCreate,
    ProjectAssetRead,
    ProjectAssetUpdate,
)
from app.modules.infra.services import project_asset_service as svc

router = APIRouter(prefix="/api/v1/project-assets", tags=["infra-project-assets"])


@router.get("", response_model=list[ProjectAssetRead])
def list_project_assets(
    project_id: int | None = None,
    asset_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectAssetRead]:
    if project_id:
        return svc.list_by_project(db, project_id)
    if asset_id:
        return svc.list_by_asset(db, asset_id)
    return []


@router.post("", response_model=ProjectAssetRead, status_code=status.HTTP_201_CREATED)
def create_project_asset(
    payload: ProjectAssetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pa = svc.create_project_asset(db, payload, current_user)
    enriched = svc.list_by_project(db, pa.project_id)
    return next((r for r in enriched if r["id"] == pa.id), enriched[0])


@router.patch("/{link_id}", response_model=ProjectAssetRead)
def update_project_asset(
    link_id: int,
    payload: ProjectAssetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pa = svc.update_project_asset(db, link_id, payload, current_user)
    enriched = svc.list_by_project(db, pa.project_id)
    return next((r for r in enriched if r["id"] == pa.id), enriched[0])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_asset(
    link_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc.delete_project_asset(db, link_id, current_user)

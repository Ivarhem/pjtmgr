from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.project_customer import (
    ProjectCustomerCreate,
    ProjectCustomerRead,
    ProjectCustomerUpdate,
)
from app.modules.infra.services import project_customer_service as svc

router = APIRouter(prefix="/api/v1/project-customers", tags=["infra-project-customers"])


@router.get("", response_model=list[ProjectCustomerRead])
def list_project_customers(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectCustomerRead]:
    return svc.list_by_project(db, project_id)


@router.post("", response_model=ProjectCustomerRead, status_code=status.HTTP_201_CREATED)
def create_project_customer(
    payload: ProjectCustomerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pc = svc.create_project_customer(db, payload, current_user)
    enriched = svc.list_by_project(db, pc.project_id)
    return next((r for r in enriched if r["id"] == pc.id), enriched[0])


@router.patch("/{link_id}", response_model=ProjectCustomerRead)
def update_project_customer(
    link_id: int,
    payload: ProjectCustomerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pc = svc.update_project_customer(db, link_id, payload, current_user)
    enriched = svc.list_by_project(db, pc.project_id)
    return next((r for r in enriched if r["id"] == pc.id), enriched[0])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_customer(
    link_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc.delete_project_customer(db, link_id, current_user)

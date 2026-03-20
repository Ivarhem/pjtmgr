from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.project_customer_contact import (
    ProjectCustomerContactCreate,
    ProjectCustomerContactRead,
    ProjectCustomerContactUpdate,
)
from app.modules.infra.services import project_customer_contact_service as svc

router = APIRouter(
    prefix="/api/v1/project-customer-contacts",
    tags=["infra-project-customer-contacts"],
)


@router.get("", response_model=list[ProjectCustomerContactRead])
def list_project_customer_contacts(
    project_customer_id: int | None = None,
    project_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> list[ProjectCustomerContactRead]:
    if project_id:
        return svc.list_by_project(db, project_id)
    if project_customer_id:
        return svc.list_by_project_customer(db, project_customer_id)
    return []


@router.post(
    "", response_model=ProjectCustomerContactRead, status_code=status.HTTP_201_CREATED
)
def create_project_customer_contact(
    payload: ProjectCustomerContactCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pcc = svc.create_project_customer_contact(db, payload, current_user)
    enriched = svc.list_by_project_customer(db, pcc.project_customer_id)
    return next((r for r in enriched if r["id"] == pcc.id), enriched[0])


@router.patch("/{link_id}", response_model=ProjectCustomerContactRead)
def update_project_customer_contact(
    link_id: int,
    payload: ProjectCustomerContactUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pcc = svc.update_project_customer_contact(db, link_id, payload, current_user)
    enriched = svc.list_by_project_customer(db, pcc.project_customer_id)
    return next((r for r in enriched if r["id"] == pcc.id), enriched[0])


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_customer_contact(
    link_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    svc.delete_project_customer_contact(db, link_id, current_user)

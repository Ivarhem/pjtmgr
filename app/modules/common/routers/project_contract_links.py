"""ProjectContractLink 라우터 — 프로젝트-계약 연결 API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.common.schemas.project_contract_link import (
    ProjectContractLinkCreate,
    ProjectContractLinkRead,
)
from app.modules.common.services import project_contract_link as svc

router = APIRouter(
    prefix="/api/v1/project-contract-links",
    tags=["project-contract-links"],
)


@router.post("", response_model=ProjectContractLinkRead, status_code=201)
def create_link(
    data: ProjectContractLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectContractLinkRead:
    """프로젝트-계약 연결 생성."""
    return svc.link_project_contract(db, data, current_user)


@router.delete("/{link_id}", status_code=204)
def delete_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """프로젝트-계약 연결 삭제."""
    svc.unlink(db, link_id, current_user)


@router.get("", response_model=list[ProjectContractLinkRead])
def list_links(
    project_id: int | None = Query(None),
    contract_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectContractLinkRead]:
    """프로젝트 또는 계약 기준으로 연결 목록 조회."""
    if project_id is not None:
        return svc.list_by_project(db, project_id)
    if contract_id is not None:
        return svc.list_by_contract(db, contract_id)
    return []

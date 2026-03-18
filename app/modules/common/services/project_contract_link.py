"""ProjectContractLink 서비스 — 프로젝트-계약 연결 관리.

cross-module 모델 import 없이 SQLAlchemy text() 쿼리로 enrichment 수행.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.project_contract_link import ProjectContractLink
from app.modules.common.models.user import User
from app.modules.common.schemas.project_contract_link import (
    ProjectContractLinkCreate,
    ProjectContractLinkRead,
)


def _check_admin(user: User) -> None:
    """관리자 권한 확인."""
    if not user.role_obj or not user.role_obj.permissions.get("admin", False):
        raise PermissionDeniedError("관리자 권한이 필요합니다.")


def _enrich_link(db: Session, link: ProjectContractLink) -> ProjectContractLinkRead:
    """링크에 project_name, contract_code 를 enrichment하여 Read 스키마로 변환."""
    project_name: str | None = None
    contract_code: str | None = None

    row = db.execute(
        text("SELECT name FROM projects WHERE id = :pid"),
        {"pid": link.project_id},
    ).first()
    if row:
        project_name = row[0]

    row = db.execute(
        text("SELECT contract_code FROM contracts WHERE id = :cid"),
        {"cid": link.contract_id},
    ).first()
    if row:
        contract_code = row[0]

    return ProjectContractLinkRead(
        id=link.id,
        project_id=link.project_id,
        contract_id=link.contract_id,
        is_primary=link.is_primary,
        note=link.note,
        project_name=project_name,
        contract_code=contract_code,
    )


def link_project_contract(
    db: Session,
    payload: ProjectContractLinkCreate,
    current_user: User,
) -> ProjectContractLinkRead:
    """프로젝트-계약 연결 생성. 중복 시 DuplicateError."""
    _check_admin(current_user)

    existing = (
        db.query(ProjectContractLink)
        .filter(
            ProjectContractLink.project_id == payload.project_id,
            ProjectContractLink.contract_id == payload.contract_id,
        )
        .first()
    )
    if existing:
        raise DuplicateError("이미 연결된 프로젝트-계약 관계입니다.")

    link = ProjectContractLink(
        project_id=payload.project_id,
        contract_id=payload.contract_id,
        is_primary=payload.is_primary,
        note=payload.note,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return _enrich_link(db, link)


def unlink(
    db: Session,
    link_id: int,
    current_user: User,
) -> None:
    """프로젝트-계약 연결 삭제."""
    _check_admin(current_user)

    link = db.get(ProjectContractLink, link_id)
    if not link:
        raise NotFoundError("연결을 찾을 수 없습니다.")
    db.delete(link)
    db.commit()


def list_by_project(
    db: Session,
    project_id: int,
) -> list[ProjectContractLinkRead]:
    """프로젝트에 연결된 계약 목록 반환."""
    links = (
        db.query(ProjectContractLink)
        .filter(ProjectContractLink.project_id == project_id)
        .order_by(ProjectContractLink.is_primary.desc(), ProjectContractLink.id)
        .all()
    )
    return [_enrich_link(db, link) for link in links]


def list_by_contract(
    db: Session,
    contract_id: int,
) -> list[ProjectContractLinkRead]:
    """계약에 연결된 프로젝트 목록 반환."""
    links = (
        db.query(ProjectContractLink)
        .filter(ProjectContractLink.contract_id == contract_id)
        .order_by(ProjectContractLink.is_primary.desc(), ProjectContractLink.id)
        .all()
    )
    return [_enrich_link(db, link) for link in links]

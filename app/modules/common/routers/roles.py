"""Role CRUD 라우터 (관리자 전용)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_admin
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.common.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.modules.common.services import role as svc

router = APIRouter(
    prefix="/api/v1/roles",
    tags=["roles"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[RoleRead])
def list_roles(db: Session = Depends(get_db)) -> list[RoleRead]:
    return svc.list_roles(db)


@router.get("/{role_id}", response_model=RoleRead)
def get_role(role_id: int, db: Session = Depends(get_db)) -> RoleRead:
    return svc.get_role(db, role_id)


@router.post("", response_model=RoleRead, status_code=201)
def create_role(data: RoleCreate, db: Session = Depends(get_db)) -> RoleRead:
    return svc.create_role(db, data)


@router.patch("/{role_id}", response_model=RoleRead)
def update_role(
    role_id: int, data: RoleUpdate, db: Session = Depends(get_db)
) -> RoleRead:
    return svc.update_role(db, role_id, data)


@router.delete("/{role_id}", status_code=204)
def delete_role(role_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_role(db, role_id)

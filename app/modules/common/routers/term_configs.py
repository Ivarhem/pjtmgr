from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth.dependencies import get_current_user, require_admin
from app.modules.common.models.user import User
from app.modules.common.schemas.term_config import TermConfigRead, TermConfigCreate, TermConfigUpdate
from app.modules.common.services import term_config as svc

router = APIRouter(prefix="/api/v1/term-configs", tags=["term-configs"])


@router.get("", response_model=list[TermConfigRead])
def list_terms(
    active_only: bool = Query(True),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[TermConfigRead]:
    return svc.list_terms(db, active_only=active_only, category=category)


@router.get("/labels", response_model=dict[str, str])
def get_ui_labels(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict[str, str]:
    """모든 활성 용어의 {term_key: ui_label} 맵 반환. 프론트엔드 라벨 바인딩용."""
    return svc.list_ui_labels(db)


@router.get("/{term_key}", response_model=TermConfigRead)
def get_term(
    term_key: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> TermConfigRead:
    return svc.get_term(db, term_key)


@router.post("", response_model=TermConfigRead, status_code=201)
def create_term(
    data: TermConfigCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> TermConfigRead:
    return svc.create_term(db, data=data.model_dump())


@router.patch("/{term_key}", response_model=TermConfigRead)
def update_term(
    term_key: str,
    data: TermConfigUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> TermConfigRead:
    return svc.update_term(db, term_key, updates=data.model_dump(exclude_unset=True))


@router.post("/{term_key}/reset", response_model=TermConfigRead)
def reset_term(
    term_key: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> TermConfigRead:
    """커스텀 라벨을 기본값으로 초기화."""
    return svc.reset_term(db, term_key)


@router.delete("/{term_key}", status_code=204)
def delete_term(
    term_key: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_term(db, term_key)

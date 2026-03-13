from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.term_config import TermConfigRead, TermConfigCreate, TermConfigUpdate
from app.services import term_config as svc

router = APIRouter(prefix="/api/v1/term-configs", tags=["term-configs"])


def _to_read(t) -> TermConfigRead:
    return TermConfigRead(
        term_key=t.term_key,
        category=t.category,
        standard_label_en=t.standard_label_en,
        standard_label_ko=t.standard_label_ko,
        definition=t.definition,
        default_ui_label=t.default_ui_label,
        custom_ui_label=t.custom_ui_label,
        ui_label=t.ui_label,
        is_customized=t.is_customized,
        is_active=t.is_active,
        sort_order=t.sort_order,
    )


@router.get("", response_model=list[TermConfigRead])
def list_terms(
    active_only: bool = Query(True),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return [_to_read(t) for t in svc.list_terms(db, active_only=active_only, category=category)]


@router.get("/labels", response_model=dict[str, str])
def get_ui_labels(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """모든 활성 용어의 {term_key: ui_label} 맵 반환. 프론트엔드 라벨 바인딩용."""
    return svc.list_ui_labels(db)


@router.get("/{term_key}", response_model=TermConfigRead)
def get_term(
    term_key: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return _to_read(svc.get_term(db, term_key))


@router.post("", response_model=TermConfigRead, status_code=201)
def create_term(
    data: TermConfigCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    term = svc.create_term(db, data=data.model_dump())
    return _to_read(term)


@router.patch("/{term_key}", response_model=TermConfigRead)
def update_term(
    term_key: str,
    data: TermConfigUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    term = svc.update_term(db, term_key, updates=data.model_dump(exclude_unset=True))
    return _to_read(term)


@router.post("/{term_key}/reset", response_model=TermConfigRead)
def reset_term(
    term_key: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """커스텀 라벨을 기본값으로 초기화."""
    term = svc.reset_term(db, term_key)
    return _to_read(term)


@router.delete("/{term_key}", status_code=204)
def delete_term(
    term_key: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    svc.delete_term(db, term_key)

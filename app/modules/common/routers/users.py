from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth.dependencies import require_admin
from app.modules.common.schemas.user import UserCreate, UserUpdate, UserRead
from app.modules.common.services import user as svc
from app.core.file_validation import validate_csv

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)):
    return svc.list_users(db)


@router.post("", response_model=UserRead, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    return svc.create_user(db, data)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)) -> None:
    svc.delete_user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db)):
    return svc.update_user(db, user_id, data)


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db)) -> dict:
    """비밀번호를 login_id로 초기화 (다음 로그인 시 변경 강제)"""
    svc.reset_password(db, user_id)
    return {"ok": True}


@router.post("/import-csv")
async def import_contacts_csv(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    """아웃룩 연락처 CSV 임포트 (utf-8-sig / utf-8 / cp949 / euc-kr 자동 감지)"""
    validate_csv(file.filename, file.content_type)
    content = await file.read()
    return svc.import_contacts_csv(db, content)

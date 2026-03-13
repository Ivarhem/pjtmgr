from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import require_admin
from app.schemas.user import UserCreate, UserUpdate, UserRead
from app.services import user as svc
from app.exceptions import BusinessRuleError

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
def delete_user(user_id: int, db: Session = Depends(get_db)):
    svc.delete_user(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db)):
    return svc.update_user(db, user_id, data)


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, db: Session = Depends(get_db)):
    """비밀번호를 login_id로 초기화 (다음 로그인 시 변경 강제)"""
    svc.reset_password(db, user_id)
    return {"ok": True}


_ALLOWED_CSV_EXTENSIONS = {".csv"}
_ALLOWED_CSV_MIMES = {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}


@router.post("/import-csv")
async def import_contacts_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """아웃룩 연락처 CSV 임포트 (utf-8-sig / utf-8 / cp949 / euc-kr 자동 감지)"""
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_CSV_EXTENSIONS:
        raise BusinessRuleError("CSV 파일만 업로드할 수 있습니다. (.csv)", status_code=422)
    if file.content_type and file.content_type not in _ALLOWED_CSV_MIMES:
        raise BusinessRuleError("CSV 파일만 업로드할 수 있습니다. (.csv)", status_code=422)
    content = await file.read()
    try:
        result = svc.import_contacts_csv(db, content)
    except ValueError as e:
        raise BusinessRuleError(str(e), status_code=422)
    return result

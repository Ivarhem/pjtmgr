"""인증 API 라우터: 로그인, 로그아웃, 비밀번호 변경."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.service import authenticate
from app.auth.password import hash_password, verify_password
from app.auth.dependencies import get_current_user
from app.auth.authorization import get_permissions
from app.models.user import User
from app.exceptions import BusinessRuleError, PermissionDeniedError, UnauthorizedError
from app.schemas.auth import ChangePasswordRequest, LoginRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    user = authenticate(db, data.login_id, data.password)
    if not user:
        raise UnauthorizedError("아이디 또는 비밀번호가 올바르지 않습니다.")
    request.session["user_id"] = user.id
    return {"must_change_password": user.must_change_password}


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not current_user.hashed_password or not verify_password(
        data.current_password, current_user.hashed_password
    ):
        raise BusinessRuleError("현재 비밀번호가 올바르지 않습니다.", status_code=400)
    MIN_PASSWORD_LENGTH = 4
    if len(data.new_password) < MIN_PASSWORD_LENGTH:
        raise BusinessRuleError(f"새 비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.", status_code=400)
    current_user.hashed_password = hash_password(data.new_password)
    current_user.must_change_password = False
    db.commit()
    return {"ok": True}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "name": current_user.name,
        "role": current_user.role,
        "department": current_user.department,
        "must_change_password": current_user.must_change_password,
        "permissions": get_permissions(current_user),
    }

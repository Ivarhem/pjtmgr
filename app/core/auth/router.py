"""인증 API 라우터: 로그인, 로그아웃, 비밀번호 변경."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth.service import authenticate, change_password as svc_change_password
from app.core.auth.dependencies import get_current_user
from app.core.auth.authorization import get_permissions
from app.modules.common.models.user import User
from app.core.exceptions import UnauthorizedError
from app.modules.common.schemas.auth import ChangePasswordRequest, LoginRequest

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
    svc_change_password(db, current_user, data.current_password, data.new_password)
    return {"ok": True}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "name": current_user.name,
        "role": current_user.role_obj.name if current_user.role_obj else None,
        "role_id": current_user.role_id,
        "department": current_user.department,
        "must_change_password": current_user.must_change_password,
        "permissions": get_permissions(current_user),
    }

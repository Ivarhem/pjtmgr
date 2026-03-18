"""FastAPI 의존성: 현재 로그인 사용자 확인 및 권한 검사."""
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.common.models.user import User
from app.core.auth.constants import ROLE_ADMIN
from app.core.exceptions import PermissionDeniedError, UnauthorizedError


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """세션에서 로그인된 사용자를 반환. 미인증 시 401."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise UnauthorizedError("로그인이 필요합니다.")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("로그인이 필요합니다.")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """관리자 권한 확인. 미인증 시 401, 권한 부족 시 403."""
    if current_user.role != ROLE_ADMIN:
        raise PermissionDeniedError("관리자 권한이 필요합니다.")
    return current_user

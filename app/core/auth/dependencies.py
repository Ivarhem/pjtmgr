"""FastAPI 의존성: 현재 로그인 사용자 확인 및 권한 검사."""
from fastapi import Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.core.auth.authorization import get_module_access_level
from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.modules.common.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """세션에서 로그인된 사용자를 반환. 미인증 시 401. role_obj를 eagerly load."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise UnauthorizedError("로그인이 필요합니다.")
    user = (
        db.query(User)
        .options(joinedload(User.role_obj))
        .filter(User.id == user_id)
        .first()
    )
    if not user or not user.is_active:
        raise UnauthorizedError("로그인이 필요합니다.")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """관리자 권한 확인. 미인증 시 401, 권한 부족 시 403."""
    if not current_user.role_obj or not current_user.role_obj.permissions.get("admin", False):
        raise PermissionDeniedError("관리자 권한이 필요합니다.")
    return current_user


def require_module_access(module: str, min_level: str = "read"):
    """라우터 Depends로 사용. read/full 수준 검사.

    Usage:
        router = APIRouter(dependencies=[require_module_access("accounting", "full")])
        # or on individual endpoints:
        @router.get("/...", dependencies=[require_module_access("accounting", "read")])
    """

    def checker(current_user: User = Depends(get_current_user)) -> User:
        level = get_module_access_level(current_user, module)
        if level is None:
            raise PermissionDeniedError("모듈 접근 권한이 없습니다.")
        if min_level == "full" and level == "read":
            raise PermissionDeniedError("읽기 전용 권한입니다.")
        return current_user

    return Depends(checker)

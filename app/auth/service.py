"""인증 서비스: 자격증명 검증, 비밀번호 변경."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.config import LOGIN_LOCKOUT_SECONDS, LOGIN_MAX_FAILURES
from app.models.user import User
from app.auth.password import hash_password, verify_password
from app.exceptions import BusinessRuleError
from app.services.setting import get_password_min_length


_LOGIN_FAILURES: dict[str, dict[str, datetime | int | None]] = {}


def _now() -> datetime:
    return datetime.now(UTC)


def reset_login_failures() -> None:
    """테스트/운영 정비용 로그인 실패 상태 초기화."""
    _LOGIN_FAILURES.clear()


def _get_lock_state(login_id: str) -> dict[str, datetime | int | None]:
    return _LOGIN_FAILURES.setdefault(login_id, {"count": 0, "locked_until": None})


def _is_locked(login_id: str) -> bool:
    state = _LOGIN_FAILURES.get(login_id)
    if not state:
        return False
    locked_until = state.get("locked_until")
    if not isinstance(locked_until, datetime):
        return False
    if _now() >= locked_until:
        _LOGIN_FAILURES.pop(login_id, None)
        return False
    return True


def _record_failure(login_id: str) -> None:
    state = _get_lock_state(login_id)
    count = int(state["count"] or 0) + 1
    state["count"] = count
    if count >= LOGIN_MAX_FAILURES:
        state["locked_until"] = _now() + timedelta(seconds=LOGIN_LOCKOUT_SECONDS)


def _clear_failures(login_id: str) -> None:
    _LOGIN_FAILURES.pop(login_id, None)


def authenticate(db: Session, login_id: str, password: str) -> User | None:
    """login_id + password 검증. 성공 시 활성 User 반환, 실패 시 None."""
    if _is_locked(login_id):
        return None
    user = (
        db.query(User)
        .filter(User.login_id == login_id, User.is_active.is_(True))
        .first()
    )
    if not user or not user.hashed_password:
        _record_failure(login_id)
        return None
    if not verify_password(password, user.hashed_password):
        _record_failure(login_id)
        return None
    _clear_failures(login_id)
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    """비밀번호 변경. 현재 비밀번호 검증 후 새 비밀번호로 교체."""
    if not user.hashed_password or not verify_password(current_password, user.hashed_password):
        raise BusinessRuleError("현재 비밀번호가 올바르지 않습니다.", status_code=400)
    min_length = get_password_min_length(db)
    if len(new_password) < min_length:
        raise BusinessRuleError(f"새 비밀번호는 {min_length}자 이상이어야 합니다.", status_code=400)
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    db.commit()

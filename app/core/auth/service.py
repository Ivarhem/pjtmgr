"""인증 서비스: 자격증명 검증, 비밀번호 변경."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import LOGIN_LOCKOUT_SECONDS, LOGIN_MAX_FAILURES
from app.modules.common.models.login_failure import LoginFailure
from app.modules.common.models.user import User
from app.core.auth.password import hash_password, verify_password
from app.core.exceptions import BusinessRuleError
from app.modules.common.services.setting import get_password_min_length


def _now() -> datetime:
    return datetime.now(UTC)


def reset_login_failures(db: Session) -> None:
    """테스트/운영 정비용 로그인 실패 상태 초기화."""
    db.query(LoginFailure).delete()
    db.commit()


def _get_or_create_failure(db: Session, login_id: str) -> LoginFailure:
    row = db.query(LoginFailure).filter(LoginFailure.login_id == login_id).first()
    if not row:
        row = LoginFailure(login_id=login_id, failure_count=0, locked_until=None)
        db.add(row)
        db.flush()
    return row


def _is_locked(db: Session, login_id: str) -> bool:
    row = db.query(LoginFailure).filter(LoginFailure.login_id == login_id).first()
    if not row or not row.locked_until:
        return False
    locked = row.locked_until
    now = _now()
    # SQLite는 timezone-naive datetime을 반환하므로 통일
    if locked.tzinfo is None and now.tzinfo is not None:
        locked = locked.replace(tzinfo=now.tzinfo)
    elif locked.tzinfo is not None and now.tzinfo is None:
        now = now.replace(tzinfo=locked.tzinfo)
    if now >= locked:
        row.failure_count = 0
        row.locked_until = None
        db.flush()
        return False
    return True


def _record_failure(db: Session, login_id: str) -> None:
    row = _get_or_create_failure(db, login_id)
    row.failure_count += 1
    if row.failure_count >= LOGIN_MAX_FAILURES:
        row.locked_until = _now() + timedelta(seconds=LOGIN_LOCKOUT_SECONDS)
    db.flush()


def _clear_failures(db: Session, login_id: str) -> None:
    db.query(LoginFailure).filter(LoginFailure.login_id == login_id).delete()
    db.flush()


def authenticate(db: Session, login_id: str, password: str) -> User | None:
    """login_id + password 검증. 성공 시 활성 User 반환, 실패 시 None."""
    if _is_locked(db, login_id):
        db.commit()
        return None
    user = (
        db.query(User)
        .filter(User.login_id == login_id, User.is_active.is_(True))
        .first()
    )
    if not user or not user.hashed_password:
        _record_failure(db, login_id)
        db.commit()
        return None
    if not verify_password(password, user.hashed_password):
        _record_failure(db, login_id)
        db.commit()
        return None
    _clear_failures(db, login_id)
    db.commit()
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

"""인증 서비스: 자격증명 검증, 비밀번호 변경."""
from sqlalchemy.orm import Session
from app.models.user import User
from app.auth.password import hash_password, verify_password
from app.exceptions import BusinessRuleError


def authenticate(db: Session, login_id: str, password: str) -> User | None:
    """login_id + password 검증. 성공 시 활성 User 반환, 실패 시 None."""
    user = (
        db.query(User)
        .filter(User.login_id == login_id, User.is_active.is_(True))
        .first()
    )
    if not user or not user.hashed_password:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    """비밀번호 변경. 현재 비밀번호 검증 후 새 비밀번호로 교체."""
    if not user.hashed_password or not verify_password(current_password, user.hashed_password):
        raise BusinessRuleError("현재 비밀번호가 올바르지 않습니다.", status_code=400)
    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    db.commit()

"""인증 서비스: 자격증명 검증."""
from sqlalchemy.orm import Session
from app.models.user import User
from app.auth.password import verify_password


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

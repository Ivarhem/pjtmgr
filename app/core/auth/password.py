"""비밀번호 해싱 및 검증 (bcrypt)."""
import bcrypt


def hash_password(password: str) -> str:
    """비밀번호를 bcrypt로 해싱하여 문자열로 반환."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """비밀번호와 해시를 비교하여 일치 여부 반환."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

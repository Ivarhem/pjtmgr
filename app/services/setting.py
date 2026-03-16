from sqlalchemy.orm import Session
from app.config import PASSWORD_MIN_LENGTH
from app.models.setting import Setting


def get_setting(db: Session, key: str) -> str | None:
    row = db.get(Setting, key)
    return row.value if row else None


def update_setting(db: Session, key: str, value: str | None) -> None:
    row = db.get(Setting, key)
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))
    db.commit()


def get_password_min_length(db: Session) -> int:
    value = get_setting(db, "auth.password_min_length")
    if value is None or value == "":
        return PASSWORD_MIN_LENGTH
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return PASSWORD_MIN_LENGTH
    return parsed if 8 <= parsed <= 64 else PASSWORD_MIN_LENGTH

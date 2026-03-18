from sqlalchemy.orm import Session
from app.modules.common.models.user_preference import UserPreference


def get_preference(db: Session, user_id: int, key: str) -> str | None:
    row = db.get(UserPreference, (user_id, key))
    return row.value if row else None


def update_preference(db: Session, user_id: int, key: str, value: str | None) -> None:
    row = db.get(UserPreference, (user_id, key))
    if row:
        row.value = value
    else:
        db.add(UserPreference(user_id=user_id, key=key, value=value))
    db.commit()

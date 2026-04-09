from sqlalchemy.orm import Session
from app.core.config import PASSWORD_MIN_LENGTH
from app.modules.common.models.setting import Setting


def get_setting(db: Session, key: str) -> str | None:
    row = db.get(Setting, key)
    return row.value if row else None


def update_setting(db: Session, key: str, value: str | None) -> None:
    _set_setting_value(db, key, value)
    db.commit()


def _set_setting_value(db: Session, key: str, value: str | None) -> None:
    row = db.get(Setting, key)
    if row:
        row.value = value
    else:
        db.add(Setting(key=key, value=value))


def update_settings(db: Session, data: "SettingUpdate") -> None:
    """SettingUpdate 스키마 기반 일괄 설정 업데이트."""
    from app.modules.common.schemas.setting import SettingUpdate  # noqa: F811

    updates = data.model_dump(exclude_unset=True)
    if "org_name" in updates:
        _set_setting_value(db, "org_name", updates["org_name"] or None)
    if "password_min_length" in updates:
        _set_setting_value(db, "auth.password_min_length", str(updates["password_min_length"]))
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

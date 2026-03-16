from pydantic import BaseModel, field_validator

from app.config import PASSWORD_MIN_LENGTH


def _validate_password_min_length(v: int | None) -> int | None:
    if v is None:
        return None
    if v < 8 or v > 64:
        raise ValueError("비밀번호 최소 길이는 8자 이상 64자 이하여야 합니다.")
    return v


class SettingsRead(BaseModel):
    org_name: str | None = None
    password_min_length: int = PASSWORD_MIN_LENGTH


class SettingsUpdate(BaseModel):
    org_name: str | None = None
    password_min_length: int | None = None

    @field_validator("password_min_length")
    @classmethod
    def validate_password_min_length(cls, v: int | None) -> int | None:
        return _validate_password_min_length(v)

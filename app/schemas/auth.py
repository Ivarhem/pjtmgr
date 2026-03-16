from pydantic import BaseModel, field_validator

MIN_PASSWORD_LENGTH = 8


class LoginRequest(BaseModel):
    login_id: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"새 비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.")
        return v

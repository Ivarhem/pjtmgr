from pydantic import BaseModel


class LoginRequest(BaseModel):
    login_id: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

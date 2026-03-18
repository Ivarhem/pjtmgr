from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    department: str | None = None
    position: str | None = None
    login_id: str | None = None          # SSO 연동 시 매핑 기준
    role_id: int


class UserUpdate(BaseModel):
    name: str | None = None
    department: str | None = None
    position: str | None = None
    login_id: str | None = None
    role_id: int | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: int
    name: str
    department: str | None
    position: str | None
    login_id: str | None
    role_id: int
    is_active: bool

    model_config = {"from_attributes": True}

from pydantic import BaseModel


class RoleCreate(BaseModel):
    name: str
    permissions: dict


class RoleUpdate(BaseModel):
    name: str | None = None
    permissions: dict | None = None


class RoleRead(BaseModel):
    id: int
    name: str
    is_system: bool
    permissions: dict

    model_config = {"from_attributes": True}

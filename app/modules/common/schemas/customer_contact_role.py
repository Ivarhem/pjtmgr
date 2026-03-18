from typing import Literal
from pydantic import BaseModel

RoleType = Literal["영업", "세금계산서", "업무"]
VALID_ROLE_TYPES = {"영업", "세금계산서", "업무"}


class CustomerContactRoleCreate(BaseModel):
    role_type: RoleType
    is_default: bool = False


class CustomerContactRoleRead(BaseModel):
    id: int
    role_type: str
    is_default: bool

    model_config = {"from_attributes": True}

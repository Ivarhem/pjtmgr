from pydantic import BaseModel, field_validator
from app.schemas.customer_contact_role import CustomerContactRoleCreate, CustomerContactRoleRead

# 하위호환
VALID_CONTACT_TYPES = {"영업", "세금계산서", "업무"}


class CustomerContactCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    roles: list[CustomerContactRoleCreate]

    @field_validator("roles")
    @classmethod
    def at_least_one_role(cls, v: list[CustomerContactRoleCreate]) -> list[CustomerContactRoleCreate]:
        if not v:
            raise ValueError("최소 1개 이상의 역할을 지정해야 합니다.")
        return v


class CustomerContactUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    roles: list[CustomerContactRoleCreate] | None = None


class CustomerContactRead(BaseModel):
    id: int
    customer_id: int
    name: str
    phone: str | None
    email: str | None
    roles: list[CustomerContactRoleRead]

    model_config = {"from_attributes": True}

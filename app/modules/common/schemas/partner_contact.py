from pydantic import BaseModel, field_validator
from app.modules.common.schemas.partner_contact_role import PartnerContactRoleCreate, PartnerContactRoleRead

# 하위호환
VALID_CONTACT_TYPES = {"영업", "세금계산서", "업무"}


class PartnerContactCreate(BaseModel):
    name: str
    phone: str | None = None
    email: str | None = None
    department: str | None = None
    title: str | None = None
    emergency_phone: str | None = None
    note: str | None = None
    roles: list[PartnerContactRoleCreate]

    @field_validator("roles")
    @classmethod
    def at_least_one_role(cls, v: list[PartnerContactRoleCreate]) -> list[PartnerContactRoleCreate]:
        if not v:
            raise ValueError("최소 1개 이상의 역할을 지정해야 합니다.")
        return v


class PartnerContactUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    department: str | None = None
    title: str | None = None
    emergency_phone: str | None = None
    note: str | None = None
    roles: list[PartnerContactRoleCreate] | None = None


class PartnerContactRead(BaseModel):
    id: int
    partner_id: int
    name: str
    phone: str | None
    email: str | None
    department: str | None = None
    title: str | None = None
    emergency_phone: str | None = None
    note: str | None = None
    roles: list[PartnerContactRoleRead]

    model_config = {"from_attributes": True}

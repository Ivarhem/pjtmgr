from pydantic import BaseModel
from app.modules.common.schemas.partner_contact import PartnerContactRead


class PartnerCreate(BaseModel):
    name: str
    business_no: str | None = None
    notes: str | None = None
    partner_type: str | None = None
    phone: str | None = None
    address: str | None = None
    note: str | None = None


class PartnerUpdate(BaseModel):
    name: str | None = None
    business_no: str | None = None
    notes: str | None = None
    partner_type: str | None = None
    phone: str | None = None
    address: str | None = None
    note: str | None = None


class PartnerRead(BaseModel):
    id: int
    partner_code: str
    name: str
    business_no: str | None
    notes: str | None
    partner_type: str | None = None
    phone: str | None = None
    address: str | None = None
    note: str | None = None
    contacts: list[PartnerContactRead] = []

    model_config = {"from_attributes": True}


class PartnerListRead(BaseModel):
    id: int
    partner_code: str
    name: str
    business_no: str | None
    notes: str | None
    partner_type: str | None = None
    phone: str | None = None
    address: str | None = None
    note: str | None = None
    contacts: list[PartnerContactRead] = []
    active_count: int = 0
    total_revenue: int = 0

    model_config = {"from_attributes": True}

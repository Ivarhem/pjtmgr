from pydantic import BaseModel
from app.modules.common.schemas.customer_contact import CustomerContactRead


class CustomerCreate(BaseModel):
    name: str
    business_no: str | None = None
    notes: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    business_no: str | None = None
    notes: str | None = None


class CustomerRead(BaseModel):
    id: int
    name: str
    business_no: str | None
    notes: str | None
    contacts: list[CustomerContactRead] = []

    model_config = {"from_attributes": True}


class CustomerListRead(BaseModel):
    id: int
    name: str
    business_no: str | None
    notes: str | None
    contacts: list[CustomerContactRead] = []
    active_count: int = 0
    total_revenue: int = 0

    model_config = {"from_attributes": True}

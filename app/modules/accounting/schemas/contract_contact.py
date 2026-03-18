from typing import Literal
from pydantic import BaseModel

ContactType = Literal["영업", "세금계산서", "업무"]
RankType = Literal["정", "부"]


class ContractContactCreate(BaseModel):
    customer_id: int
    customer_contact_id: int
    contact_type: ContactType
    rank: RankType = "정"
    notes: str | None = None


class ContractContactUpdate(BaseModel):
    customer_contact_id: int | None = None
    contact_type: ContactType | None = None
    rank: RankType | None = None
    notes: str | None = None


class ContractContactRead(BaseModel):
    id: int
    contract_period_id: int
    customer_id: int
    customer_contact_id: int | None
    contact_type: str
    rank: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None

    model_config = {"from_attributes": True}

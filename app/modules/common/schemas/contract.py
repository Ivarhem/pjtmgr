from typing import Literal

from pydantic import BaseModel

ContractStatus = Literal["active", "closed", "cancelled"]


class ContractCreate(BaseModel):
    contract_name: str
    contract_type: str
    end_customer_id: int | None = None
    owner_user_id: int | None = None
    status: ContractStatus = "active"
    notes: str | None = None


class ContractUpdate(BaseModel):
    contract_name: str | None = None
    contract_type: str | None = None
    contract_code: str | None = None
    end_customer_id: int | None = None
    owner_user_id: int | None = None
    status: ContractStatus | None = None
    notes: str | None = None


class ContractRead(BaseModel):
    id: int
    contract_code: str | None
    contract_name: str
    contract_type: str
    end_customer_id: int | None
    end_customer_name: str | None = None
    owner_user_id: int | None
    owner_name: str | None = None
    status: str
    notes: str | None = None

    model_config = {"from_attributes": True}


class BulkAssignOwnerRequest(BaseModel):
    contract_ids: list[int]
    owner_user_id: int | None = None

from pydantic import BaseModel


class ProjectContractLinkCreate(BaseModel):
    project_id: int
    contract_id: int
    is_primary: bool = False
    note: str | None = None


class ProjectContractLinkUpdate(BaseModel):
    is_primary: bool | None = None
    note: str | None = None


class ProjectContractLinkRead(BaseModel):
    id: int
    project_id: int
    contract_id: int
    is_primary: bool
    note: str | None
    project_name: str | None = None
    contract_code: str | None = None

    model_config = {"from_attributes": True}

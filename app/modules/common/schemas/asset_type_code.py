from pydantic import BaseModel, Field


class AssetTypeCodeRead(BaseModel):
    type_key: str
    code: str
    label: str
    sort_order: int
    is_active: bool


class AssetTypeCodeCreate(BaseModel):
    type_key: str = Field(pattern=r'^[a-z][a-z0-9_]{0,29}$')
    code: str = Field(pattern=r'^[A-Z]{3}$')
    label: str = Field(min_length=1, max_length=50)
    sort_order: int = 0


class AssetTypeCodeUpdate(BaseModel):
    label: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None

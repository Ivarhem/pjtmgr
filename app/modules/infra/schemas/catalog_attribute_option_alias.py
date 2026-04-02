from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CatalogAttributeOptionAliasBase(BaseModel):
    alias_value: str = Field(min_length=1, max_length=150)
    match_type: str = Field(default="normalized_exact", max_length=20)
    sort_order: int = 100
    is_active: bool = True


class CatalogAttributeOptionAliasCreate(CatalogAttributeOptionAliasBase):
    attribute_key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    option_id: int | None = None
    option_key: str | None = Field(default=None, min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")


class CatalogAttributeOptionAliasUpdate(BaseModel):
    alias_value: str | None = Field(default=None, min_length=1, max_length=150)
    attribute_key: str | None = Field(default=None, min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    option_id: int | None = None
    option_key: str | None = Field(default=None, min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    match_type: str | None = Field(default=None, max_length=20)
    sort_order: int | None = None
    is_active: bool | None = None


class CatalogAttributeOptionAliasRead(CatalogAttributeOptionAliasBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attribute_option_id: int
    normalized_alias: str
    attribute_id: int
    attribute_key: str
    attribute_label: str
    option_id: int
    option_key: str
    option_label: str
    mapped_product_count: int = 0

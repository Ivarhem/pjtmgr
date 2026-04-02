from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CatalogAttributeBase(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    value_type: str = Field(default="option", pattern="^(option|text)$")
    is_required: bool = False
    is_display_required: bool = False
    is_displayable: bool = True
    is_system: bool = False
    multi_value: bool = False
    sort_order: int = 100
    is_active: bool = True

    @model_validator(mode="after")
    def validate_display_requirement(self):
        if self.is_display_required and not self.is_displayable:
            raise ValueError("display_required 속성은 displayable 이어야 합니다.")
        if self.multi_value:
            raise ValueError("1차 구현에서는 multi_value=true를 허용하지 않습니다.")
        return self


class CatalogAttributeCreate(CatalogAttributeBase):
    attribute_key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")


class CatalogAttributeUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    value_type: str | None = Field(default=None, pattern="^(option|text)$")
    is_required: bool | None = None
    is_display_required: bool | None = None
    is_displayable: bool | None = None
    is_system: bool | None = None
    multi_value: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update_flags(self):
        if self.is_display_required is True and self.is_displayable is False:
            raise ValueError("display_required 속성은 displayable 이어야 합니다.")
        if self.multi_value is True:
            raise ValueError("1차 구현에서는 multi_value=true를 허용하지 않습니다.")
        return self


class CatalogAttributeRead(CatalogAttributeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attribute_key: str

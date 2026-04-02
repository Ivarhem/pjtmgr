from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductCatalogAttributeValueWrite(BaseModel):
    attribute_key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    option_key: str | None = Field(default=None, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    raw_value: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_value_source(self):
        if not self.option_key and (self.raw_value is None or not self.raw_value.strip()):
            raise ValueError("option_key 또는 raw_value 중 하나는 필요합니다.")
        return self


class ProductCatalogAttributesUpdate(BaseModel):
    attributes: list[ProductCatalogAttributeValueWrite]

    @model_validator(mode="after")
    def validate_unique_attributes(self):
        keys = [item.attribute_key for item in self.attributes]
        if len(keys) != len(set(keys)):
            raise ValueError("동일 attribute_key를 중복 저장할 수 없습니다.")
        required_keys = {"domain", "imp_type"}
        missing = sorted(required_keys - set(keys))
        if missing:
            raise ValueError(f"필수 속성이 누락되었습니다: {', '.join(missing)}")
        return self


class ProductCatalogAttributeValueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    attribute_id: int
    option_id: int | None = None
    raw_value: str | None = None
    sort_order: int
    is_primary: bool
    attribute_key: str
    attribute_label: str
    option_key: str | None = None
    option_label: str | None = None

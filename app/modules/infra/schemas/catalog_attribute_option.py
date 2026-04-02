from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HANGUL_RE = re.compile(r"[\uAC00-\uD7A3\u3130-\u318F]")


class CatalogAttributeOptionBase(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    label_kr: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int = 100
    is_active: bool = True

    @field_validator("label")
    @classmethod
    def label_must_not_contain_korean(cls, v: str) -> str:
        if _HANGUL_RE.search(v):
            raise ValueError("영문 라벨에는 한글을 포함할 수 없습니다.")
        return v


class CatalogAttributeOptionCreate(CatalogAttributeOptionBase):
    option_key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    domain_option_id: int | None = None


class CatalogAttributeOptionUpdate(BaseModel):
    option_key: str | None = Field(default=None, min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    label: str | None = Field(default=None, min_length=1, max_length=100)
    label_kr: str | None = None
    description: str | None = Field(default=None, max_length=1000)
    sort_order: int | None = None
    is_active: bool | None = None
    domain_option_id: int | None = None

    @field_validator("label")
    @classmethod
    def label_must_not_contain_korean(cls, v: str | None) -> str | None:
        if v is not None and _HANGUL_RE.search(v):
            raise ValueError("영문 라벨에는 한글을 포함할 수 없습니다.")
        return v


class CatalogAttributeOptionRead(CatalogAttributeOptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attribute_id: int
    option_key: str
    domain_option_id: int | None = None
    domain_option_key: str | None = None
    domain_option_label: str | None = None
    label_kr: str | None = None
    domain_option_label_kr: str | None = None
    aliases: list[dict] = Field(default_factory=list)

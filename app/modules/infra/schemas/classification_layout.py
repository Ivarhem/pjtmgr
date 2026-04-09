from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.infra.services.classification_identity_service import (
    PRIMARY_LAYOUT_ATTRIBUTE_KEYS,
    is_valid_primary_layout_attribute,
)


class ClassificationLayoutLevelKeyWrite(BaseModel):
    attribute_key: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    sort_order: int = 100
    is_visible: bool = True


class ClassificationLayoutLevelWrite(BaseModel):
    level_no: int = Field(ge=1, le=10)
    alias: str = Field(min_length=1, max_length=100)
    joiner: str | None = Field(default=None, max_length=20)
    prefix_mode: str | None = Field(default=None, max_length=30)
    sort_order: int = 100
    keys: list[ClassificationLayoutLevelKeyWrite]

    @model_validator(mode="after")
    def validate_level_keys(self):
        if not self.keys:
            raise ValueError("각 레벨에는 최소 하나의 속성이 필요합니다.")
        if len(self.keys) != 1:
            raise ValueError("각 레벨에는 정확히 하나의 속성만 배치할 수 있습니다.")
        keys = [item.attribute_key for item in self.keys]
        if len(keys) != len(set(keys)):
            raise ValueError("같은 레벨에 동일 속성을 중복 배치할 수 없습니다.")
        return self


class ClassificationLayoutBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    depth_count: int = Field(default=3, ge=1, le=10)
    is_default: bool = False
    is_active: bool = True


class ClassificationLayoutCreate(ClassificationLayoutBase):
    scope_type: str = Field(default="global", pattern="^(global|project)$")
    project_id: int | None = None
    levels: list[ClassificationLayoutLevelWrite]

    @model_validator(mode="after")
    def validate_levels(self):
        return _validate_layout_levels(self)


class ClassificationLayoutUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    depth_count: int | None = Field(default=None, ge=1, le=10)
    is_default: bool | None = None
    is_active: bool | None = None
    levels: list[ClassificationLayoutLevelWrite] | None = None

    @model_validator(mode="after")
    def validate_optional_levels(self):
        if self.levels is None:
            return self
        return _validate_layout_levels(self)


class ClassificationLayoutRead(ClassificationLayoutBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope_type: str
    project_id: int | None = None


def _validate_layout_levels(model):
    level_nos = [level.level_no for level in model.levels]
    if len(level_nos) != len(set(level_nos)):
        raise ValueError("level_no는 중복될 수 없습니다.")
    if model.depth_count != len(model.levels):
        raise ValueError("depth_count와 실제 level 수가 일치해야 합니다.")
    all_keys = [
        key.attribute_key
        for level in model.levels
        for key in level.keys
    ]
    if "vendor_series" in set(all_keys):
        raise ValueError("vendor_series는 분류 레이아웃 키로 사용할 수 없습니다.")
    if len(all_keys) != len(set(all_keys)):
        raise ValueError("같은 레이아웃에 동일 속성을 중복 배치할 수 없습니다.")
    if all_keys.count("domain") != 1 or all_keys.count("imp_type") != 1:
        raise ValueError("레이아웃에는 domain과 imp_type가 각각 정확히 1회 포함되어야 합니다.")
    if "domain" not in set(all_keys):
        raise ValueError("레이아웃에는 display_required 속성인 domain이 최소 1회 포함되어야 합니다.")
    level_one = next((level for level in model.levels if level.level_no == 1), None)
    if level_one is None:
        raise ValueError("레이아웃에는 level 1이 필요합니다.")
    level_one_key = level_one.keys[0].attribute_key if level_one.keys else None
    if not is_valid_primary_layout_attribute(level_one_key):
        allowed = ", ".join(sorted(PRIMARY_LAYOUT_ATTRIBUTE_KEYS))
        raise ValueError(f"level 1에는 {allowed} 중 하나만 배치할 수 있습니다.")
    return model

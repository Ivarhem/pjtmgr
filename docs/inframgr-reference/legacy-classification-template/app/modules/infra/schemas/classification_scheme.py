from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassificationSchemeCreate(BaseModel):
    scope_type: str
    project_id: int | None = None
    name: str
    description: str | None = None
    level_1_alias: str | None = None
    level_2_alias: str | None = None
    level_3_alias: str | None = None
    level_4_alias: str | None = None
    level_5_alias: str | None = None
    is_active: bool = True


class ClassificationSchemeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    level_1_alias: str | None = None
    level_2_alias: str | None = None
    level_3_alias: str | None = None
    level_4_alias: str | None = None
    level_5_alias: str | None = None
    is_active: bool | None = None


class ClassificationSchemeCopyRequest(BaseModel):
    target_project_id: int | None = None
    name: str | None = None
    description: str | None = None


class ClassificationSchemeInitRequest(BaseModel):
    mode: str
    source_scheme_id: int | None = None
    name: str | None = None
    description: str | None = None


class ClassificationSchemeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scope_type: str
    project_id: int | None = None
    project_label: str | None = None
    name: str
    description: str | None = None
    level_1_alias: str | None = None
    level_2_alias: str | None = None
    level_3_alias: str | None = None
    level_4_alias: str | None = None
    level_5_alias: str | None = None
    source_scheme_id: int | None = None
    source_scheme_name: str | None = None
    is_active: bool
    node_count: int = 0
    created_at: datetime
    updated_at: datetime

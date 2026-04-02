from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClassificationNodeCreate(BaseModel):
    node_code: str
    node_name: str
    parent_id: int | None = None
    level: int | None = None
    sort_order: int = 100
    is_active: bool = True
    asset_type_key: str | None = None
    asset_type_code: str | None = None
    asset_type_label: str | None = None
    asset_kind: str | None = None
    is_catalog_assignable: bool = False
    note: str | None = None


class ClassificationNodeUpdate(BaseModel):
    node_code: str | None = None
    node_name: str | None = None
    parent_id: int | None = None
    level: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    asset_type_key: str | None = None
    asset_type_code: str | None = None
    asset_type_label: str | None = None
    asset_kind: str | None = None
    is_catalog_assignable: bool | None = None
    note: str | None = None


class ClassificationNodeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scheme_id: int
    parent_id: int | None = None
    node_code: str
    node_name: str
    level: int
    sort_order: int
    is_active: bool
    asset_type_key: str | None = None
    asset_type_code: str | None = None
    asset_type_label: str | None = None
    asset_kind: str | None = None
    is_catalog_assignable: bool = False
    note: str | None = None
    path_label: str | None = None
    created_at: datetime
    updated_at: datetime

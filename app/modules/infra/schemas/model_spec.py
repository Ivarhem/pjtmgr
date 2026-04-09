from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelSpecCreate(BaseModel):
    provider: str | None = None
    model_family: str | None = None
    modality: str | None = None
    deployment_scope: str | None = None
    context_window: int | None = None
    endpoint_format: str | None = None
    capability_note: str | None = None


class ModelSpecUpdate(BaseModel):
    provider: str | None = None
    model_family: str | None = None
    modality: str | None = None
    deployment_scope: str | None = None
    context_window: int | None = None
    endpoint_format: str | None = None
    capability_note: str | None = None


class ModelSpecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    provider: str | None
    model_family: str | None
    modality: str | None
    deployment_scope: str | None
    context_window: int | None
    endpoint_format: str | None
    capability_note: str | None

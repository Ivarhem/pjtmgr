from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SoftwareSpecCreate(BaseModel):
    edition: str | None = None
    license_type: str | None = None
    license_unit: str | None = None
    deployment_type: str | None = None
    runtime_env: str | None = None
    support_vendor: str | None = None
    architecture_note: str | None = None


class SoftwareSpecUpdate(BaseModel):
    edition: str | None = None
    license_type: str | None = None
    license_unit: str | None = None
    deployment_type: str | None = None
    runtime_env: str | None = None
    support_vendor: str | None = None
    architecture_note: str | None = None


class SoftwareSpecRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    edition: str | None
    license_type: str | None
    license_unit: str | None
    deployment_type: str | None
    runtime_env: str | None
    support_vendor: str | None
    architecture_note: str | None

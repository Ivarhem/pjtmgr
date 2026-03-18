from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PolicyDefinitionCreate(BaseModel):
    policy_code: str
    policy_name: str
    category: str
    description: str | None = None
    is_active: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    security_domain: str | None = None
    requirement: str | None = None
    architecture_element: str | None = None
    control_point: str | None = None
    iso27001_ref: str | None = None
    nist_ref: str | None = None
    isms_p_ref: str | None = None
    implementation_example: str | None = None
    evidence: str | None = None


class PolicyDefinitionUpdate(BaseModel):
    policy_code: str | None = None
    policy_name: str | None = None
    category: str | None = None
    description: str | None = None
    is_active: bool | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    security_domain: str | None = None
    requirement: str | None = None
    architecture_element: str | None = None
    control_point: str | None = None
    iso27001_ref: str | None = None
    nist_ref: str | None = None
    isms_p_ref: str | None = None
    implementation_example: str | None = None
    evidence: str | None = None


class PolicyDefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_code: str
    policy_name: str
    category: str
    description: str | None
    is_active: bool
    effective_from: date | None
    effective_to: date | None
    security_domain: str | None
    requirement: str | None
    architecture_element: str | None
    control_point: str | None
    iso27001_ref: str | None
    nist_ref: str | None
    isms_p_ref: str | None
    implementation_example: str | None
    evidence: str | None
    created_at: datetime
    updated_at: datetime

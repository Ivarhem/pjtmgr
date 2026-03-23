from typing import Literal

from pydantic import BaseModel, field_validator

from app.core._normalize import normalize_month

Stage = Literal["10%", "50%", "70%", "90%", "계약완료", "실주"]


class ContractPeriodCreate(BaseModel):
    period_year: int
    period_label: str | None = None
    stage: Stage = "50%"
    start_month: str | None = None
    end_month: str | None = None
    description: str | None = None
    owner_user_id: int | None = None
    customer_id: int | None = None
    is_planned: bool = True
    notes: str | None = None

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month_fields(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v


class ContractPeriodUpdate(BaseModel):
    period_label: str | None = None
    stage: Stage | None = None
    is_planned: bool | None = None
    start_month: str | None = None
    end_month: str | None = None
    description: str | None = None
    owner_user_id: int | None = None
    customer_id: int | None = None
    is_completed: bool | None = None
    notes: str | None = None

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month_fields(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v


class ContractPeriodRead(BaseModel):
    id: int
    contract_id: int
    period_year: int
    period_label: str
    period_code: str
    stage: str
    start_month: str | None = None
    end_month: str | None = None
    description: str | None = None
    owner_user_id: int | None = None
    owner_name: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    is_completed: bool = False
    is_planned: bool = True
    notes: str | None = None

    model_config = {"from_attributes": True}

from pydantic import BaseModel, field_validator
from typing import Literal


class ReceiptMatchCreate(BaseModel):
    receipt_id: int
    transaction_line_id: int
    matched_amount: int
    match_type: Literal["auto", "manual"] = "manual"

    @field_validator("matched_amount")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("대사 금액은 0보다 커야 합니다.")
        return v


class ReceiptMatchUpdate(BaseModel):
    matched_amount: int

    @field_validator("matched_amount")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("대사 금액은 0보다 커야 합니다.")
        return v


class ReceiptMatchRead(BaseModel):
    id: int
    receipt_id: int
    transaction_line_id: int
    matched_amount: int
    match_type: str
    # 조회 편의 필드
    receipt_date: str | None = None
    revenue_month: str | None = None
    partner_name: str | None = None
    supply_amount: int | None = None

    model_config = {"from_attributes": True}

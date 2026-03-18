from pydantic import BaseModel, field_validator
from app.core._normalize import normalize_month, normalize_date


class ReceiptCreate(BaseModel):
    customer_id: int | None = None
    receipt_date: str           # YYYY-MM-DD
    revenue_month: str | None = None   # YYYY-MM-01 (귀속월 연결)
    amount: int
    description: str | None = None

    @field_validator("receipt_date")
    @classmethod
    def validate_receipt_date(cls, v: str) -> str:
        return normalize_date(v)

    @field_validator("revenue_month")
    @classmethod
    def validate_revenue_month(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v


class ReceiptUpdate(BaseModel):
    customer_id: int | None = None
    receipt_date: str | None = None
    revenue_month: str | None = None
    amount: int | None = None
    description: str | None = None

    @field_validator("receipt_date")
    @classmethod
    def validate_receipt_date(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_date(v)
        return v

    @field_validator("revenue_month")
    @classmethod
    def validate_revenue_month(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v


class ReceiptRead(BaseModel):
    id: int
    contract_id: int
    customer_id: int | None
    customer_name: str | None
    receipt_date: str
    revenue_month: str | None
    amount: int
    description: str | None

    model_config = {"from_attributes": True}

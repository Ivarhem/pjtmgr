from typing import Literal
from pydantic import BaseModel, field_validator
from app.schemas._normalize import normalize_month, normalize_date

LineType = Literal["revenue", "cost"]
TransactionLineStatus = Literal["예정", "확정"]


class TransactionLineCreate(BaseModel):
    revenue_month: str          # YYYY-MM-01 (귀속월)
    line_type: LineType         # revenue / cost
    customer_id: int | None = None
    customer_name: str | None = None    # id가 없을 때 이름으로 자동 생성
    supply_amount: int
    invoice_issue_date: str | None = None   # YYYY-MM-DD
    status: TransactionLineStatus | None = None      # 예정/확정 (None이면 자동 판별)
    description: str | None = None

    @field_validator("revenue_month")
    @classmethod
    def validate_revenue_month(cls, v: str) -> str:
        return normalize_month(v)

    @field_validator("invoice_issue_date")
    @classmethod
    def validate_invoice_date(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_date(v)
        return v


class TransactionLineUpdate(BaseModel):
    revenue_month: str | None = None
    line_type: LineType | None = None
    customer_id: int | None = None
    customer_name: str | None = None    # id가 없을 때 이름으로 자동 생성
    supply_amount: int | None = None
    invoice_issue_date: str | None = None
    status: TransactionLineStatus | None = None
    description: str | None = None

    @field_validator("revenue_month")
    @classmethod
    def validate_revenue_month(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v

    @field_validator("invoice_issue_date")
    @classmethod
    def validate_invoice_date(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_date(v)
        return v


class TransactionLineRead(BaseModel):
    id: int
    contract_id: int
    revenue_month: str
    line_type: str
    customer_id: int | None
    customer_name: str | None
    supply_amount: int
    invoice_issue_date: str | None
    status: str
    description: str | None

    model_config = {"from_attributes": True}

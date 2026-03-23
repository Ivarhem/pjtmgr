from pydantic import BaseModel, field_validator
from app.core._normalize import normalize_date


class ContractSalesDetailRead(BaseModel):
    id: int
    contract_period_id: int
    expected_revenue_amount: int = 0
    expected_gp_amount: int = 0
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None

    model_config = {"from_attributes": True}


class ContractSalesDetailUpdate(BaseModel):
    expected_revenue_amount: int | None = None
    expected_gp_amount: int | None = None
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None

    @field_validator("inspection_date")
    @classmethod
    def validate_inspection_date(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_date(v)
        return v

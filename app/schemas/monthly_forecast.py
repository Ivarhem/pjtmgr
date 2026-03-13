from pydantic import BaseModel, field_validator
from app.schemas._normalize import normalize_month


class MonthlyForecastCreate(BaseModel):
    forecast_month: str   # YYYY-MM-01
    revenue_amount: int = 0
    gp_amount: int = 0

    @field_validator("forecast_month")
    @classmethod
    def validate_forecast_month(cls, v: str) -> str:
        return normalize_month(v)


class MonthlyForecastRead(BaseModel):
    id: int
    contract_period_id: int
    forecast_month: str
    revenue_amount: int
    gp_amount: int
    version_no: int
    is_current: bool

    model_config = {"from_attributes": True}

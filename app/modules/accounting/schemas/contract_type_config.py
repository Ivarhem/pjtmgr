from pydantic import BaseModel


class ContractTypeRead(BaseModel):
    code: str
    label: str
    sort_order: int
    is_active: bool
    default_gp_pct: int | None = None
    default_inspection_day: int | None = None
    default_invoice_month_offset: int | None = None
    default_invoice_day_type: str | None = None
    default_invoice_day: int | None = None
    default_invoice_holiday_adjust: str | None = None


class ContractTypeCreate(BaseModel):
    code: str
    label: str
    sort_order: int = 0
    default_gp_pct: int | None = None
    default_inspection_day: int | None = None
    default_invoice_month_offset: int | None = None
    default_invoice_day_type: str | None = None
    default_invoice_day: int | None = None
    default_invoice_holiday_adjust: str | None = None


class ContractTypeUpdate(BaseModel):
    label: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    default_gp_pct: int | None = None
    default_inspection_day: int | None = None
    default_invoice_month_offset: int | None = None
    default_invoice_day_type: str | None = None
    default_invoice_day: int | None = None
    default_invoice_holiday_adjust: str | None = None

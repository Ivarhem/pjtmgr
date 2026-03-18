from typing import Literal

from pydantic import BaseModel, field_validator

from app.core._normalize import normalize_date, normalize_month

Stage = Literal["10%", "50%", "70%", "90%", "계약완료", "실주"]
ContractStatus = Literal["active", "closed", "cancelled"]

VALID_STAGES = {"10%", "50%", "70%", "90%", "계약완료", "실주"}
VALID_STATUSES = {"active", "closed", "cancelled"}


# ── Contract ──────────────────────────────────────────────────────
class ContractCreate(BaseModel):
    contract_name: str
    contract_type: str  # DB의 ContractTypeConfig에서 동적 검증
    end_customer_id: int | None = None
    owner_user_id: int | None = None
    status: ContractStatus = "active"
    notes: str | None = None


InvoiceDayType = Literal["1일", "말일", "특정일"]
InvoiceHolidayAdjust = Literal["전", "후"]


class ContractUpdate(BaseModel):
    contract_name: str | None = None
    contract_type: str | None = None
    contract_code: str | None = None
    end_customer_id: int | None = None
    owner_user_id: int | None = None
    status: ContractStatus | None = None
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None
    notes: str | None = None

    @field_validator("inspection_date")
    @classmethod
    def validate_inspection_date(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_date(v)
        return v


class ContractRead(BaseModel):
    id: int
    contract_code: str | None
    contract_name: str
    contract_type: str
    end_customer_id: int | None
    end_customer_name: str | None
    owner_user_id: int | None
    owner_name: str | None
    status: str
    notes: str | None = None
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None

    model_config = {"from_attributes": True}


# ── Bulk Operations ──────────────────────────────────────────────
class BulkAssignOwnerRequest(BaseModel):
    contract_ids: list[int]
    owner_user_id: int | None = None


# ── ContractPeriod ────────────────────────────────────────────────
class ContractPeriodCreate(BaseModel):
    period_year: int
    period_label: str | None = None
    stage: Stage = "50%"
    expected_revenue_total: int = 0
    expected_gp_total: int = 0
    start_month: str | None = None    # YYYY-MM-01
    end_month: str | None = None      # YYYY-MM-01
    owner_user_id: int | None = None  # 미지정 시 Contract의 값을 복사
    customer_id: int | None = None    # 매출처 (미지정 시 Contract의 end_customer_id를 복사)
    # 검수/세금계산서 발행 규칙 (미지정 시 Contract의 값을 복사)
    is_planned: bool = True               # 연초 보고 사업 여부
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None
    notes: str | None = None

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month_fields(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v

    @field_validator("inspection_date")
    @classmethod
    def validate_inspection_date(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_date(v)
        return v


class ContractPeriodUpdate(BaseModel):
    period_label: str | None = None
    stage: Stage | None = None
    is_planned: bool | None = None
    expected_revenue_total: int | None = None
    expected_gp_total: int | None = None
    start_month: str | None = None
    end_month: str | None = None
    owner_user_id: int | None = None
    customer_id: int | None = None
    is_completed: bool | None = None
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None
    notes: str | None = None

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month_fields(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v

    @field_validator("inspection_date")
    @classmethod
    def validate_inspection_date(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_date(v)
        return v


class ContractPeriodRead(BaseModel):
    id: int
    contract_id: int
    period_year: int
    period_label: str
    stage: str
    expected_revenue_total: int
    expected_gp_total: int
    start_month: str | None = None
    end_month: str | None = None
    owner_user_id: int | None = None
    owner_name: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    is_completed: bool = False
    is_planned: bool = True
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None
    notes: str | None

    model_config = {"from_attributes": True}



class ContractPeriodListRead(BaseModel):
    """원장 목록용 - contract + period 조인 결과"""
    id: int              # contract_period.id
    contract_id: int
    contract_code: str | None
    contract_name: str
    contract_type: str
    end_customer_name: str | None
    customer_name: str | None          # Period별 매출처
    owner_name: str | None
    status: str
    period_year: int
    period_label: str
    stage: str
    expected_revenue_total: int
    expected_gp_total: int
    is_planned: bool = True

    model_config = {"from_attributes": True}

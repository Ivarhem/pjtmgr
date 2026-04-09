"""Accounting-specific contract schemas. Common schemas re-exported from common module."""
from typing import Literal

from pydantic import BaseModel

# Re-export common schemas
from app.modules.common.schemas.contract import (  # noqa: F401
    ContractCreate,
    ContractRead,
    ContractUpdate,
    ContractStatus,
    BulkAssignOwnerRequest,
)
from app.modules.common.schemas.contract_period import (  # noqa: F401
    ContractPeriodCreate,
    ContractPeriodRead,
    ContractPeriodUpdate,
    Stage,
)

VALID_STAGES = {"10%", "50%", "70%", "90%", "계약완료", "실주"}
VALID_STATUSES = {"active", "closed", "cancelled"}
InvoiceDayType = Literal["1일", "말일", "특정일"]
InvoiceHolidayAdjust = Literal["전", "후"]


class ContractPeriodListRead(BaseModel):
    """원장 목록용 - contract + period + sales_detail 조인 결과"""
    id: int              # contract_period.id
    contract_id: int
    contract_code: str | None
    contract_name: str
    contract_type: str
    end_partner_name: str | None
    partner_name: str | None
    owner_name: str | None
    status: str
    period_year: int
    period_label: str
    period_code: str
    stage: str
    expected_revenue_amount: int = 0  # was _total
    expected_gp_amount: int = 0       # was _total
    is_planned: bool = True

    model_config = {"from_attributes": True}

"""보고서 응답 스키마."""
from __future__ import annotations

from pydantic import BaseModel


# ── 공통 필터 ────────────────────────────────────────────────────

class ReportFilter(BaseModel):
    """보고서 공통 필터 (서비스 레이어 내부용)."""
    date_from: str          # YYYY-MM-01
    date_to: str            # YYYY-MM-01
    owner_id: list[int] | None = None
    department: list[str] | None = None
    contract_type: list[str] | None = None
    stage: list[str] | None = None
    basis: str = "revenue_month"   # 향후 확장: invoice_month 등


# ── 요약 현황 ────────────────────────────────────────────────────

class SummaryKPI(BaseModel):
    forecast_revenue: int = 0
    actual_revenue: int = 0
    cost: int = 0
    gp: int = 0
    gp_pct: float | None = None
    receipt: int = 0
    ar: int = 0
    achievement_rate: float | None = None   # actual_revenue / forecast_revenue


class MonthlySummaryRow(BaseModel):
    month: str                  # YYYY-MM
    forecast_revenue: int = 0
    actual_revenue: int = 0
    cost: int = 0
    gp: int = 0
    gp_pct: float | None = None
    receipt: int = 0
    ar: int = 0


class SummaryResponse(BaseModel):
    kpis: SummaryKPI
    period_summary: list[MonthlySummaryRow]


# ── Forecast vs Actual ───────────────────────────────────────────

class ForecastActualRow(BaseModel):
    contract_id: int
    contract_period_id: int
    contract_name: str
    contract_type: str
    owner_name: str | None = None
    department: str | None = None
    end_customer_name: str | None = None
    stage: str | None = None
    forecast_revenue: int = 0
    actual_revenue: int = 0
    gap_revenue: int = 0              # forecast - actual
    achievement_rate: float | None = None
    gp: int = 0
    gp_pct: float | None = None


class ForecastActualResponse(BaseModel):
    rows: list[ForecastActualRow]
    totals: ForecastActualRow | None = None


# ── 미수 현황 ────────────────────────────────────────────────────

class ReceivableRow(BaseModel):
    contract_id: int
    contract_name: str
    contract_type: str
    owner_name: str | None = None
    department: str | None = None
    end_customer_name: str | None = None
    actual_revenue: int = 0
    receipt: int = 0
    ar: int = 0
    ar_rate: float | None = None    # ar / actual_revenue


class ReceivableTotals(BaseModel):
    actual_revenue: int = 0
    receipt: int = 0
    ar: int = 0
    ar_rate: float | None = None


class ReceivableResponse(BaseModel):
    rows: list[ReceivableRow]
    totals: ReceivableTotals

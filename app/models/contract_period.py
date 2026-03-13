"""사업 기간 (ContractPeriod) - 계약 주기 단위 (Y25, Y26 등)"""
from sqlalchemy import String, Integer, ForeignKey, Date, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime
from app.database import Base
from app.models.base import TimestampMixin


class ContractPeriod(TimestampMixin, Base):
    __tablename__ = "contract_periods"
    __table_args__ = (UniqueConstraint("contract_id", "period_year", name="uq_contract_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)        # 2025, 2026
    period_label: Mapped[str] = mapped_column(String(20), nullable=False)    # Y25, Y26
    stage: Mapped[str] = mapped_column(String(50), nullable=False)           # 10%/50%/70%/90%/계약완료
    expected_revenue_total: Mapped[int] = mapped_column(Integer, default=0)  # 예상 수익 (원)
    expected_gp_total: Mapped[int] = mapped_column(Integer, default=0)      # 예상 GP (원)
    start_month: Mapped[str | None] = mapped_column(String(10))            # 시작월 (YYYY-MM-01)
    end_month: Mapped[str | None] = mapped_column(String(10))              # 종료월 (YYYY-MM-01)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))  # Period별 담당 영업
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))  # 매출처 (미지정 시 Contract.end_customer)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)      # 계약기간 완료 여부
    notes: Mapped[str | None] = mapped_column(String(500))

    # 검수/세금계산서 발행 규칙 (Period별 독립 — 갱신 계약 시 조건 변경 가능)
    inspection_day: Mapped[int | None] = mapped_column(Integer)             # MA: 검수일 (매월 N일, 0=말일)
    inspection_date: Mapped[datetime.date | None] = mapped_column(Date)     # 비MA: 특정 검수일자
    invoice_month_offset: Mapped[int | None] = mapped_column(Integer)       # 발행 기준월 (0=당월, 1=익월)
    invoice_day_type: Mapped[str | None] = mapped_column(String(20))        # 발행일 유형: 1일/말일/특정일
    invoice_day: Mapped[int | None] = mapped_column(Integer)                # 특정일인 경우 날짜
    invoice_holiday_adjust: Mapped[str | None] = mapped_column(String(10))  # 휴일 조정: 전/후

    contract: Mapped["Contract"] = relationship(back_populates="periods")
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_user_id])
    customer: Mapped["Customer | None"] = relationship(foreign_keys=[customer_id])
    forecasts: Mapped[list["MonthlyForecast"]] = relationship(
        back_populates="contract_period", cascade="all, delete-orphan",
        order_by="MonthlyForecast.forecast_month"
    )
    contract_contacts: Mapped[list["ContractContact"]] = relationship(
        back_populates="contract_period", cascade="all, delete-orphan"
    )

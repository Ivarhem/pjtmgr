"""월별 Forecast - 예상 매출/GP (contract_period 단위)"""
from sqlalchemy import String, Integer, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class MonthlyForecast(TimestampMixin, Base):
    __tablename__ = "monthly_forecasts"
    __table_args__ = (
        UniqueConstraint("contract_period_id", "forecast_month", "version_no", name="uq_forecast"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_period_id: Mapped[int] = mapped_column(ForeignKey("contract_periods.id"), nullable=False, index=True)
    forecast_month: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-01
    revenue_amount: Mapped[int] = mapped_column(Integer, default=0)           # 예상 수익 (원)
    gp_amount: Mapped[int] = mapped_column(Integer, default=0)               # 예상 GP (원)
    version_no: Mapped[int] = mapped_column(Integer, default=1)              # 버전 (스냅샷용)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)  # 최신 버전 여부
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    contract_period: Mapped["ContractPeriod"] = relationship(back_populates="forecasts")

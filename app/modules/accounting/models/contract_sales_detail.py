"""영업 확장 정보 (ContractSalesDetail) - ContractPeriod 1:1 영업 전용 필드."""
import datetime
from sqlalchemy import String, Integer, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class ContractSalesDetail(TimestampMixin, Base):
    __tablename__ = "contract_sales_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_period_id: Mapped[int] = mapped_column(
        ForeignKey("contract_periods.id"), unique=True, nullable=False
    )
    expected_revenue_amount: Mapped[int] = mapped_column(Integer, default=0)
    expected_gp_amount: Mapped[int] = mapped_column(Integer, default=0)
    inspection_day: Mapped[int | None] = mapped_column(Integer)
    inspection_date: Mapped[datetime.date | None] = mapped_column(Date)
    invoice_month_offset: Mapped[int | None] = mapped_column(Integer)
    invoice_day_type: Mapped[str | None] = mapped_column(String(20))
    invoice_day: Mapped[int | None] = mapped_column(Integer)
    invoice_holiday_adjust: Mapped[str | None] = mapped_column(String(10))

    contract_period: Mapped["ContractPeriod"] = relationship()

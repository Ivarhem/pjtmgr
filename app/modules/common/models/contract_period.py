"""사업 기간 (ContractPeriod) - 계약 주기 단위 (Y25, Y26 등). 공통 기본정보."""
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class ContractPeriod(TimestampMixin, Base):
    __tablename__ = "contract_periods"
    __table_args__ = (UniqueConstraint("contract_id", "period_year", name="uq_contract_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(20), nullable=False)
    period_code: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    start_month: Mapped[str | None] = mapped_column(String(10), index=True)
    end_month: Mapped[str | None] = mapped_column(String(10), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_planned: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(500))

    contract: Mapped["Contract"] = relationship(back_populates="periods")
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_user_id])
    customer: Mapped["Customer | None"] = relationship(foreign_keys=[customer_id])
    # Note: forecasts, contract_contacts relationships는 accounting 모델 측에서
    # backref로 정의한다 (common → accounting 역방향 의존 방지).

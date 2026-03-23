"""사업 (Contract) - 하나의 사업/프로젝트 본체. 공통 기본정보."""
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_code: Mapped[str | None] = mapped_column(String(50), unique=True)
    contract_name: Mapped[str] = mapped_column(String(300), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    end_customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    notes: Mapped[str | None] = mapped_column(String(500))

    end_customer: Mapped["Customer | None"] = relationship(back_populates="contracts")
    owner: Mapped["User | None"] = relationship(back_populates="contracts")
    periods: Mapped[list["ContractPeriod"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan", order_by="ContractPeriod.period_year"
    )
    # transaction_lines, receipts relationships는 accounting 모델 측에서
    # backref로 정의한다 (common → accounting 역방향 의존 방지).

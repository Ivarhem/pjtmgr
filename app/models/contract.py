"""사업 (Contract) - 하나의 사업/프로젝트 본체"""
from sqlalchemy import String, Integer, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime
from app.database import Base
from app.models.base import TimestampMixin


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_code: Mapped[str | None] = mapped_column(String(50), unique=True)   # 내부 사업코드 (자동생성)
    contract_name: Mapped[str] = mapped_column(String(300), nullable=False)       # 사업명
    contract_type: Mapped[str] = mapped_column(String(30), nullable=False)        # MA / SI / HW / ETC
    end_customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))  # END 고객
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))  # 영업 담당
    status: Mapped[str] = mapped_column(String(30), default="active")         # active / closed / cancelled
    notes: Mapped[str | None] = mapped_column(String(500))                     # 비고

    # 검수/세금계산서 발행 규칙
    inspection_day: Mapped[int | None] = mapped_column(Integer)               # MA: 검수일 (매월 N일, 0=말일)
    inspection_date: Mapped[datetime.date | None] = mapped_column(Date)       # 비MA: 특정 검수일자
    invoice_month_offset: Mapped[int | None] = mapped_column(Integer)         # 발행 기준월 (0=당월, 1=익월)
    invoice_day_type: Mapped[str | None] = mapped_column(String(20))          # 발행일 유형: 1일/말일/특정일
    invoice_day: Mapped[int | None] = mapped_column(Integer)                  # 특정일인 경우 날짜
    invoice_holiday_adjust: Mapped[str | None] = mapped_column(String(10))    # 휴일 조정: 전/후

    end_customer: Mapped["Customer | None"] = relationship(back_populates="contracts")
    owner: Mapped["User | None"] = relationship(back_populates="contracts")
    periods: Mapped[list["ContractPeriod"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan", order_by="ContractPeriod.period_year"
    )
    transaction_lines: Mapped[list["TransactionLine"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )
    receipts: Mapped[list["Receipt"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )
    # contract_contacts는 ContractPeriod 레벨로 이동됨

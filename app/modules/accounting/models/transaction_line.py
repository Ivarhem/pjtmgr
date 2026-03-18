"""거래 라인 (TransactionLine) - 귀속월 기준, 공급가액 기준, 라인 단위"""
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin

# 상태값 상수
STATUS_EXPECTED = "예정"        # forecast에서 가져온 초기 상태
STATUS_CONFIRMED = "확정"       # 거래처·발행일 입력 완료


class TransactionLine(TimestampMixin, Base):
    __tablename__ = "transaction_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    revenue_month: Mapped[str] = mapped_column(String(10), nullable=False, index=True)   # YYYY-MM-01 (귀속월)
    line_type: Mapped[str] = mapped_column(String(20), nullable=False)       # revenue / cost
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))  # 매출처/매입처
    supply_amount: Mapped[int] = mapped_column(Integer, nullable=False)      # 공급가액 (원, VAT별도)
    invoice_issue_date: Mapped[str | None] = mapped_column(String(10))      # 세금계산서 발행일 YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(20), default=STATUS_CONFIRMED)  # 예정/확정
    description: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    contract: Mapped["Contract"] = relationship(back_populates="transaction_lines")
    customer: Mapped["Customer | None"] = relationship(back_populates="transaction_lines")
    receipt_matches: Mapped[list["ReceiptMatch"]] = relationship(
        back_populates="transaction_line", cascade="all, delete-orphan",
    )

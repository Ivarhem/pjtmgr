"""수금 (Receipt) - 공급가액 기준, contract 단위"""
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin


class Receipt(TimestampMixin, Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))  # 주로 매출처
    receipt_date: Mapped[str] = mapped_column(String(10), nullable=False)    # YYYY-MM-DD
    revenue_month: Mapped[str | None] = mapped_column(String(10))            # YYYY-MM-01 (귀속월 연결)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)             # 공급가액 기준 (원)
    description: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    contract: Mapped["Contract"] = relationship(back_populates="receipts")
    customer: Mapped["Customer | None"] = relationship(back_populates="receipts")
    matches: Mapped[list["ReceiptMatch"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan",
    )

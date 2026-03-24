"""수금 (Receipt) - 공급가액 기준, contract 단위"""
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class Receipt(TimestampMixin, Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id"))  # 주로 매출처
    receipt_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)    # YYYY-MM-DD
    revenue_month: Mapped[str | None] = mapped_column(String(10), index=True)            # YYYY-MM-01 (귀속월 연결)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)             # 공급가액 기준 (원)
    description: Mapped[str | None] = mapped_column(String(300))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    contract: Mapped["Contract"] = relationship(foreign_keys="[Receipt.contract_id]")
    partner: Mapped["Partner | None"] = relationship(foreign_keys="[Receipt.partner_id]")
    matches: Mapped[list["ReceiptMatch"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan",
    )

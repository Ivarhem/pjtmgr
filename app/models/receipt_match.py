"""수금 대사 (ReceiptMatch) - Receipt를 매출 라인(TransactionLine)에 매칭"""
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin


class ReceiptMatch(TimestampMixin, Base):
    __tablename__ = "receipt_matches"
    __table_args__ = (
        UniqueConstraint("receipt_id", "transaction_line_id", name="uq_receipt_match_receipt_transaction_line"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[int] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    transaction_line_id: Mapped[int] = mapped_column(
        ForeignKey("transaction_lines.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    matched_amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 대사 금액 (원)
    match_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="auto",  # auto / manual
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    receipt: Mapped["Receipt"] = relationship(back_populates="matches")
    transaction_line: Mapped["TransactionLine"] = relationship(back_populates="receipt_matches")

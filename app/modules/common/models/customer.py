"""거래처 (매출처/매입처 공용)"""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_no: Mapped[str | None] = mapped_column(String(50))          # 사업자번호
    notes: Mapped[str | None] = mapped_column(Text)
    customer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 고객사/공급사/유지보수사/통신사
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    contacts: Mapped[list["CustomerContact"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan",
        order_by="CustomerContact.name, CustomerContact.id",
    )
    contracts: Mapped[list["Contract"]] = relationship(back_populates="end_customer")
    # transaction_lines, receipts, contract_contacts relationships는
    # accounting 모델 측에서 정의한다 (common → accounting 역방향 의존 방지).

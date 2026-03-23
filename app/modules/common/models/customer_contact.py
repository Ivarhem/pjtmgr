"""거래처 담당자 (CustomerContact) - 거래처별 N명의 담당자 관리

담당자 1명이 여러 역할(영업/세금계산서/업무)을 겸할 수 있으며,
역할 정보는 CustomerContactRole 테이블에서 관리한다.
"""
from sqlalchemy import String, Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class CustomerContact(TimestampMixin, Base):
    __tablename__ = "customer_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(200))
    # 레거시 컬럼 — DB NOT NULL 제약 유지용 (실제 역할은 CustomerContactRole로 관리)
    contact_type: Mapped[str] = mapped_column(String(20), default="", insert_default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, insert_default=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="contacts")
    roles: Mapped[list["CustomerContactRole"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan", lazy="joined"
    )
    # contract_contacts relationship은 accounting 모델에서 정의.

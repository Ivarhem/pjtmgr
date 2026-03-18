"""사업별 담당자 (ContractContact) - Period-거래처 단위로 영업/세금계산서/업무 담당자 관리

거래처 기본담당자(CustomerContact)를 참조하여 담당자를 지정한다.
정/부 구분(rank)으로 같은 역할에 여러 명 배정 가능.
"""
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import TimestampMixin


class ContractContact(TimestampMixin, Base):
    __tablename__ = "contract_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_period_id: Mapped[int] = mapped_column(ForeignKey("contract_periods.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    customer_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("customer_contacts.id", ondelete="SET NULL"), index=True
    )
    contact_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 영업 / 세금계산서 / 업무
    rank: Mapped[str] = mapped_column(String(10), nullable=False, default="정")  # 정 / 부
    notes: Mapped[str | None] = mapped_column(String(500))

    contract_period: Mapped["ContractPeriod"] = relationship(back_populates="contract_contacts")
    customer: Mapped["Customer"] = relationship(back_populates="contract_contacts")
    customer_contact: Mapped["CustomerContact | None"] = relationship(back_populates="contract_contacts")

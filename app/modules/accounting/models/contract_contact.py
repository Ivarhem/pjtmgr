"""사업별 담당자 (ContractContact) - Period-거래처 단위로 영업/세금계산서/업무 담당자 관리

거래처 기본담당자(PartnerContact)를 참조하여 담당자를 지정한다.
정/부 구분(rank)으로 같은 역할에 여러 명 배정 가능.
"""
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class ContractContact(TimestampMixin, Base):
    __tablename__ = "contract_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_period_id: Mapped[int] = mapped_column(ForeignKey("contract_periods.id"), nullable=False, index=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), nullable=False, index=True)
    partner_contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("partner_contacts.id", ondelete="SET NULL"), index=True
    )
    contact_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 영업 / 세금계산서 / 업무
    rank: Mapped[str] = mapped_column(String(10), nullable=False, default="정")  # 정 / 부
    notes: Mapped[str | None] = mapped_column(String(500))

    contract_period: Mapped["ContractPeriod"] = relationship(foreign_keys="[ContractContact.contract_period_id]")
    partner: Mapped["Partner"] = relationship(foreign_keys="[ContractContact.partner_id]")
    partner_contact: Mapped["PartnerContact | None"] = relationship(foreign_keys="[ContractContact.partner_contact_id]")

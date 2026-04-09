"""거래처 담당자 역할 (PartnerContactRole) - 담당자 1명이 여러 역할을 가질 수 있음"""
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class PartnerContactRole(TimestampMixin, Base):
    __tablename__ = "partner_contact_roles"
    __table_args__ = (
        UniqueConstraint("partner_contact_id", "role_type", name="uq_contact_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_contact_id: Mapped[int] = mapped_column(
        ForeignKey("partner_contacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 영업 / 세금계산서 / 업무
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)    # 역할별 기본 담당자

    contact: Mapped["PartnerContact"] = relationship(back_populates="roles")

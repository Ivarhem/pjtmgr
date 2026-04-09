from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class PeriodPartnerContact(TimestampMixin, Base):
    __tablename__ = "period_partner_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period_partner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("period_partners.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("partner_contacts.id"), nullable=False, index=True
    )
    project_role: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("period_partner_id", "contact_id", "project_role"),
    )

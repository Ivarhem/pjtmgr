from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class PolicyAssignment(TimestampMixin, Base):
    __tablename__ = "policy_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    policy_definition_id: Mapped[int] = mapped_column(
        ForeignKey("policy_definitions.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="not_checked")
    exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checked_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)

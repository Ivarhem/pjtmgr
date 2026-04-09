from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class PeriodDeliverable(TimestampMixin, Base):
    __tablename__ = "period_deliverables"

    id: Mapped[int] = mapped_column(primary_key=True)
    period_phase_id: Mapped[int] = mapped_column(ForeignKey("period_phases.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

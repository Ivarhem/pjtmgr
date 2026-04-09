from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class PeriodPhase(TimestampMixin, Base):
    __tablename__ = "period_phases"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_period_id: Mapped[int] = mapped_column(ForeignKey("contract_periods.id"), index=True)
    phase_type: Mapped[str] = mapped_column(String(30))
    task_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    deliverables_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cautions: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission_required: Mapped[bool] = mapped_column(default=False)
    submission_status: Mapped[str] = mapped_column(String(30), default="pending")
    status: Mapped[str] = mapped_column(String(30), default="not_started")

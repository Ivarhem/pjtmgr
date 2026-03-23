from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class PeriodAsset(TimestampMixin, Base):
    __tablename__ = "period_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contract_periods.id"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=False, index=True
    )
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("contract_period_id", "asset_id"),)

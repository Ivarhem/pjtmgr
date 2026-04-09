from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class AssetEvent(TimestampMixin, Base):
    __tablename__ = "asset_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    related_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_id_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    asset_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )

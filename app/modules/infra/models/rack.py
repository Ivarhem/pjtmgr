from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class Rack(TimestampMixin, Base):
    __tablename__ = "racks"
    __table_args__ = (
        UniqueConstraint("room_id", "rack_code", name="uq_racks_room_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    rack_code: Mapped[str] = mapped_column(String(50), index=True)
    rack_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    total_units: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    location_detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

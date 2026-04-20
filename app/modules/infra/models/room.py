from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class Room(TimestampMixin, Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("center_id", "room_code", name="uq_rooms_center_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("centers.id", ondelete="CASCADE"), index=True)
    room_code: Mapped[str] = mapped_column(String(50), index=True)
    room_name: Mapped[str] = mapped_column(String(200))
    floor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    racks_per_row: Mapped[int] = mapped_column(Integer, default=6)
    system_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    prefix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grid_cols: Mapped[int] = mapped_column(Integer, default=10)
    grid_rows: Mapped[int] = mapped_column(Integer, default=12)

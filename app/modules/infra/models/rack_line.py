from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class RackLine(TimestampMixin, Base):
    __tablename__ = "rack_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    line_name: Mapped[str] = mapped_column(String(50))
    col_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slot_count: Mapped[int] = mapped_column(Integer)
    disabled_slots: Mapped[list] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    prefix: Mapped[str | None] = mapped_column(String(20), nullable=True)
    start_col: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_col: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    direction: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sequential_naming: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class RackLine(TimestampMixin, Base):
    __tablename__ = "rack_lines"
    __table_args__ = (
        UniqueConstraint("room_id", "col_index", name="uq_rack_lines_room_col"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    line_name: Mapped[str] = mapped_column(String(50))
    col_index: Mapped[int] = mapped_column(Integer)
    slot_count: Mapped[int] = mapped_column(Integer)
    disabled_slots: Mapped[list] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    prefix: Mapped[str | None] = mapped_column(String(20), nullable=True)

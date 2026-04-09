from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HardwareInterface(Base):
    __tablename__ = "hardware_interfaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_catalog.id", ondelete="CASCADE"), index=True
    )
    interface_type: Mapped[str] = mapped_column(String(30))
    speed: Mapped[str | None] = mapped_column(String(20), nullable=True)
    count: Mapped[int] = mapped_column(Integer)
    connector_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    capacity_type: Mapped[str] = mapped_column(String(10), default="fixed")
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

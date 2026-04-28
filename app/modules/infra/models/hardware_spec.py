from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HardwareSpec(Base):
    __tablename__ = "hardware_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_catalog.id", ondelete="CASCADE"), unique=True
    )
    size_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    depth_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    power_watt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    cpu_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    throughput_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    os_firmware: Mapped[str | None] = mapped_column(Text, nullable=True)
    spec_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

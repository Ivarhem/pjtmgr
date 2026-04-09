from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class AssetLicense(TimestampMixin, Base):
    __tablename__ = "asset_licenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    license_type: Mapped[str] = mapped_column(String(50))
    license_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_quantity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

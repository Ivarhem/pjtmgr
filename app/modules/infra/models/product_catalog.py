from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class ProductCatalog(TimestampMixin, Base):
    __tablename__ = "product_catalog"
    __table_args__ = (
        UniqueConstraint("vendor", "name", name="uq_product_catalog_vendor_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(255))
    product_type: Mapped[str] = mapped_column(String(20), default="hardware")
    category: Mapped[str] = mapped_column(String(50))
    eos_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    eosl_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    eosl_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

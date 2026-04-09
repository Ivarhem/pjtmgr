from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    eos_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    eosl_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    eosl_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_confidence: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    normalized_vendor: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(400), nullable=True, index=True)
    is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
    similar_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    default_license_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_license_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    attribute_values = relationship(
        "ProductCatalogAttributeValue",
        back_populates="product",
        cascade="all, delete-orphan",
    )

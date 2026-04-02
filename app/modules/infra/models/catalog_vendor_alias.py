from __future__ import annotations

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class CatalogVendorAlias(TimestampMixin, Base):
    __tablename__ = "catalog_vendor_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", name="uq_catalog_vendor_alias_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_canonical: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    alias_value: Mapped[str] = mapped_column(String(100), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

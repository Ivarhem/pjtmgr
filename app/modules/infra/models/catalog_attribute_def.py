from __future__ import annotations

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class CatalogAttributeDef(TimestampMixin, Base):
    __tablename__ = "catalog_attribute_defs"
    __table_args__ = (
        UniqueConstraint("attribute_key", name="uq_catalog_attribute_def_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attribute_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False, default="option")
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_display_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_displayable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    multi_value: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    options = relationship(
        "CatalogAttributeOption",
        back_populates="attribute",
        cascade="all, delete-orphan",
    )
    product_values = relationship(
        "ProductCatalogAttributeValue",
        back_populates="attribute",
    )
    layout_keys = relationship(
        "ClassificationLayoutLevelKey",
        back_populates="attribute",
    )

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class ProductCatalogAttributeValue(TimestampMixin, Base):
    __tablename__ = "product_catalog_attribute_values"
    __table_args__ = (
        UniqueConstraint("product_id", "attribute_id", name="uq_product_catalog_attribute_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_catalog.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_attribute_defs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    option_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_attribute_options.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    product = relationship("ProductCatalog", back_populates="attribute_values")
    attribute = relationship("CatalogAttributeDef", back_populates="product_values")
    option = relationship("CatalogAttributeOption", back_populates="product_values")

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class CatalogAttributeOption(TimestampMixin, Base):
    __tablename__ = "catalog_attribute_options"
    __table_args__ = (
        UniqueConstraint("attribute_id", "option_key", name="uq_catalog_attribute_option_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_attribute_defs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("catalog_attribute_options.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    option_key: Mapped[str] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    label_kr: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    attribute = relationship("CatalogAttributeDef", back_populates="options")
    domain_option = relationship("CatalogAttributeOption", remote_side=[id], foreign_keys=[domain_option_id])
    aliases = relationship(
        "CatalogAttributeOptionAlias",
        back_populates="attribute_option",
        cascade="all, delete-orphan",
    )
    product_values = relationship(
        "ProductCatalogAttributeValue",
        back_populates="option",
    )

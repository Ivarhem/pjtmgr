from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class CatalogAttributeOptionAlias(TimestampMixin, Base):
    __tablename__ = "catalog_attribute_option_aliases"
    __table_args__ = (
        UniqueConstraint("attribute_option_id", "normalized_alias", name="uq_catalog_attribute_option_alias_norm"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    attribute_option_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_attribute_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias_value: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    match_type: Mapped[str] = mapped_column(String(20), nullable=False, default="normalized_exact")
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    attribute_option = relationship("CatalogAttributeOption", back_populates="aliases")

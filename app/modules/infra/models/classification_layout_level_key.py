from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class ClassificationLayoutLevelKey(TimestampMixin, Base):
    __tablename__ = "classification_layout_level_keys"
    __table_args__ = (
        UniqueConstraint("level_id", "attribute_id", name="uq_classification_layout_level_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    level_id: Mapped[int] = mapped_column(
        ForeignKey("classification_layout_levels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("catalog_attribute_defs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    level = relationship("ClassificationLayoutLevel", back_populates="keys")
    attribute = relationship("CatalogAttributeDef", back_populates="layout_keys")

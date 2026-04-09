from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class ClassificationLayoutLevel(TimestampMixin, Base):
    __tablename__ = "classification_layout_levels"
    __table_args__ = (
        UniqueConstraint("layout_id", "level_no", name="uq_classification_layout_level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    layout_id: Mapped[int] = mapped_column(
        ForeignKey("classification_layouts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level_no: Mapped[int] = mapped_column(nullable=False)
    alias: Mapped[str] = mapped_column(String(100), nullable=False)
    joiner: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prefix_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)

    layout = relationship("ClassificationLayout", back_populates="levels")
    keys = relationship(
        "ClassificationLayoutLevelKey",
        back_populates="level",
        cascade="all, delete-orphan",
    )

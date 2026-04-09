from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class ClassificationLayout(TimestampMixin, Base):
    __tablename__ = "classification_layouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="global",
        index=True,
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("contract_periods.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    depth_count: Mapped[int] = mapped_column(nullable=False, default=3)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    levels = relationship(
        "ClassificationLayoutLevel",
        back_populates="layout",
        cascade="all, delete-orphan",
    )

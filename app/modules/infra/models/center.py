from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class Center(TimestampMixin, Base):
    __tablename__ = "centers"
    __table_args__ = (
        UniqueConstraint("partner_id", "center_code", name="uq_centers_partner_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    center_code: Mapped[str] = mapped_column(String(50), index=True)
    center_name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

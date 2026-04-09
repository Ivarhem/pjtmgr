from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class AssetRoleAssignment(TimestampMixin, Base):
    __tablename__ = "asset_role_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_role_id: Mapped[int] = mapped_column(ForeignKey("asset_roles.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    assignment_type: Mapped[str] = mapped_column(String(50), nullable=False, default="primary")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

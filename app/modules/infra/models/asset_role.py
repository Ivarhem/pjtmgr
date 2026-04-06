from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class AssetRole(TimestampMixin, Base):
    __tablename__ = "asset_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    contract_period_id: Mapped[int | None] = mapped_column(
        ForeignKey("contract_periods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

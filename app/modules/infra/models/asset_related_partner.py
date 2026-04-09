from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class AssetRelatedPartner(TimestampMixin, Base):
    __tablename__ = "asset_related_partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(50), index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

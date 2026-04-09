from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class AssetAlias(TimestampMixin, Base):
    __tablename__ = "asset_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    alias_name: Mapped[str] = mapped_column(String(255), unique=True)
    alias_type: Mapped[str] = mapped_column(String(30))
    source_partner_id: Mapped[int | None] = mapped_column(
        ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

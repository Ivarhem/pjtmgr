from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class AssetSoftware(TimestampMixin, Base):
    __tablename__ = "asset_software"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    software_name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    relation_type: Mapped[str] = mapped_column(String(30), default="installed")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

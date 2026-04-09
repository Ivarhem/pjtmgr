from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class AssetRelation(TimestampMixin, Base):
    """자산 간 범용 관계 (HOSTS, INSTALLED_ON, PROTECTS 등)."""

    __tablename__ = "asset_relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=False, index=True
    )
    dst_asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("src_asset_id != dst_asset_id", name="ck_no_self_relation"),
    )

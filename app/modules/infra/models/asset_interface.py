from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class AssetInterface(TimestampMixin, Base):
    __tablename__ = "asset_interfaces"
    __table_args__ = (
        UniqueConstraint("asset_id", "name", name="uq_asset_interface_name"),
        CheckConstraint("parent_id != id", name="ck_no_self_parent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_interfaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    hw_interface_id: Mapped[int | None] = mapped_column(
        ForeignKey("hardware_interfaces.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(100))
    if_type: Mapped[str] = mapped_column(String(30), default="physical")
    port_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    slot: Mapped[str | None] = mapped_column(String(30), nullable=True)
    slot_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    speed: Mapped[str | None] = mapped_column(String(20), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)

    admin_status: Mapped[str] = mapped_column(String(20), default="up")
    oper_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)

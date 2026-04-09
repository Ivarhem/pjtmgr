from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class AssetIP(TimestampMixin, Base):
    __tablename__ = "asset_ips"
    __table_args__ = (
        UniqueConstraint("interface_id", "ip_address", name="uq_interface_ip"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    interface_id: Mapped[int] = mapped_column(
        ForeignKey("asset_interfaces.id", ondelete="CASCADE"), index=True
    )
    ip_subnet_id: Mapped[int | None] = mapped_column(
        ForeignKey("ip_subnets.id"), index=True, nullable=True
    )
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    ip_type: Mapped[str] = mapped_column(String(30), default="service")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vlan_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

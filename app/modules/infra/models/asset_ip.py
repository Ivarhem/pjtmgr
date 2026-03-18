from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class AssetIP(TimestampMixin, Base):
    __tablename__ = "asset_ips"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    ip_subnet_id: Mapped[int | None] = mapped_column(
        ForeignKey("ip_subnets.id"), index=True, nullable=True
    )
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    ip_type: Mapped[str] = mapped_column(String(30), default="service")
    interface_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vlan_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    network: Mapped[str | None] = mapped_column(String(64), nullable=True)
    netmask: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gateway: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dns_primary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dns_secondary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class PortMap(TimestampMixin, Base):
    __tablename__ = "port_maps"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    src_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    src_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dst_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    dst_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="required")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Common
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cable_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cable_request: Mapped[str | None] = mapped_column(String(200), nullable=True)
    connection_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Start side
    src_mid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_rack_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    src_rack_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    src_vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    src_cluster: Mapped[str | None] = mapped_column(String(200), nullable=True)
    src_slot: Mapped[str | None] = mapped_column(String(30), nullable=True)
    src_port_name: Mapped[str | None] = mapped_column(String(30), nullable=True)
    src_service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    src_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    src_vlan: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # End side
    dst_mid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_rack_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dst_rack_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dst_vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dst_cluster: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dst_slot: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dst_port_name: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dst_service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    dst_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_vlan: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Cable info
    cable_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cable_speed: Mapped[str | None] = mapped_column(String(30), nullable=True)
    duplex: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cable_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

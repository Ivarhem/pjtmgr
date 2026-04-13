from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class PortMap(TimestampMixin, Base):
    __tablename__ = "port_maps"
    __table_args__ = (
        UniqueConstraint(
            "src_interface_id", "dst_interface_id", "connection_type", "protocol", "port",
            name="uq_portmap_connection",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)

    src_interface_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_interfaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dst_interface_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_interfaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    src_asset_name_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    src_interface_name_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dst_asset_name_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dst_interface_name_raw: Mapped[str | None] = mapped_column(String(100), nullable=True)

    protocol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="required")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Common
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connection_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Cable info
    cable_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cable_request: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cable_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    media_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    src_connector_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dst_connector_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cable_speed: Mapped[str | None] = mapped_column(String(30), nullable=True)
    duplex: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cable_category: Mapped[str | None] = mapped_column(String(50), nullable=True)

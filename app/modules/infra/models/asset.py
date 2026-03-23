from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.base_model import TimestampMixin


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    asset_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    asset_name: Mapped[str] = mapped_column(String(255), index=True)
    asset_type: Mapped[str] = mapped_column(String(50))
    vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    environment: Mapped[str] = mapped_column(String(30), default="prod")
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="planned")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Product Catalog 연동
    hardware_model_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_catalog.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Equipment Spec
    center: Mapped[str | None] = mapped_column(String(100), nullable=True)
    operation_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    equipment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rack_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rack_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phase: Mapped[str | None] = mapped_column(String(50), nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Logical Config
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cluster: Mapped[str | None] = mapped_column(String(200), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mgmt_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Hardware Config
    size_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lc_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ha_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    utp_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Asset Info
    asset_class: Mapped[str | None] = mapped_column(String(50), nullable=True)
    asset_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year_acquired: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dept: Mapped[str | None] = mapped_column(String(100), nullable=True)
    primary_contact_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    secondary_contact_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    maintenance_vendor: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )

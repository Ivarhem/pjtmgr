from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SoftwareSpec(Base):
    __tablename__ = "software_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_catalog.id", ondelete="CASCADE"), unique=True
    )
    edition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deployment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    runtime_env: Mapped[str | None] = mapped_column(String(100), nullable=True)
    support_vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    architecture_note: Mapped[str | None] = mapped_column(Text, nullable=True)

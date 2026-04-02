from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GenericCatalogProfile(Base):
    __tablename__ = "generic_catalog_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_catalog.id", ondelete="CASCADE"), unique=True
    )
    owner_scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    criticality: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exposure_scope: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_classification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_runtime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    summary_note: Mapped[str | None] = mapped_column(Text, nullable=True)

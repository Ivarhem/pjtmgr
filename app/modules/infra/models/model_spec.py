from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelSpec(Base):
    __tablename__ = "model_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product_catalog.id", ondelete="CASCADE"), unique=True
    )
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modality: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deployment_scope: Mapped[str | None] = mapped_column(String(50), nullable=True)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    endpoint_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capability_note: Mapped[str | None] = mapped_column(Text, nullable=True)

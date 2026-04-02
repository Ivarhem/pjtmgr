from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProductCatalogListCache(Base):
    __tablename__ = "product_catalog_list_cache"

    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("product_catalog.id", ondelete="CASCADE"),
        primary_key=True,
    )
    layout_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("classification_layouts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    cached_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

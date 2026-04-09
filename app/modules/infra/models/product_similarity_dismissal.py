from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class ProductSimilarityDismissal(TimestampMixin, Base):
    __tablename__ = "product_similarity_dismissal"
    __table_args__ = (
        UniqueConstraint("product_id_a", "product_id_b", name="uq_similarity_dismissal_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id_a: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_catalog.id", ondelete="CASCADE"), index=True
    )
    product_id_b: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_catalog.id", ondelete="CASCADE"), index=True
    )

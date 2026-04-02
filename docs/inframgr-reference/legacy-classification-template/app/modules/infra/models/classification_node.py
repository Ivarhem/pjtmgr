from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class ClassificationNode(TimestampMixin, Base):
    __tablename__ = "classification_nodes"
    __table_args__ = (
        UniqueConstraint("scheme_id", "node_code", name="uq_classification_node_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scheme_id: Mapped[int] = mapped_column(
        ForeignKey("classification_schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("classification_nodes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    node_code: Mapped[str] = mapped_column(String(50), nullable=False)
    node_name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[int] = mapped_column(nullable=False, default=1)
    sort_order: Mapped[int] = mapped_column(nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    asset_type_key: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    asset_type_code: Mapped[str | None] = mapped_column(String(3), nullable=True)
    asset_type_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    asset_kind: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_catalog_assignable: Mapped[bool] = mapped_column(default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))

    scheme = relationship("ClassificationScheme", back_populates="nodes")
    parent = relationship("ClassificationNode", remote_side=[id], foreign_keys=[parent_id])

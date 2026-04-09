from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import TimestampMixin
from app.core.database import Base


class ClassificationScheme(TimestampMixin, Base):
    __tablename__ = "classification_schemes"
    __table_args__ = (
        UniqueConstraint("scope_type", "project_id", name="uq_classification_scheme_scope_project"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("contract_periods.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    level_1_alias: Mapped[str | None] = mapped_column(String(40))
    level_2_alias: Mapped[str | None] = mapped_column(String(40))
    level_3_alias: Mapped[str | None] = mapped_column(String(40))
    level_4_alias: Mapped[str | None] = mapped_column(String(40))
    level_5_alias: Mapped[str | None] = mapped_column(String(40))
    source_scheme_id: Mapped[int | None] = mapped_column(
        ForeignKey("classification_schemes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    project = relationship("ContractPeriod", foreign_keys=[project_id])
    source_scheme = relationship("ClassificationScheme", remote_side=[id], foreign_keys=[source_scheme_id])
    nodes = relationship(
        "ClassificationNode",
        back_populates="scheme",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

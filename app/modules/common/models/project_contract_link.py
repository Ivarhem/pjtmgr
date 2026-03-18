from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class ProjectContractLink(TimestampMixin, Base):
    __tablename__ = "project_contract_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id"), nullable=False
    )
    contract_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contracts.id"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "contract_id"),)

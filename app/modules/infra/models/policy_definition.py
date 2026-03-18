from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class PolicyDefinition(TimestampMixin, Base):
    __tablename__ = "policy_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    policy_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    security_domain: Mapped[str | None] = mapped_column(String(200), nullable=True)
    requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    architecture_element: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    control_point: Mapped[str | None] = mapped_column(String(200), nullable=True)
    iso27001_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nist_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    isms_p_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    implementation_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

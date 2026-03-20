from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class ProjectCustomerContact(TimestampMixin, Base):
    __tablename__ = "project_customer_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_customers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_contacts.id"), nullable=False, index=True
    )
    project_role: Mapped[str] = mapped_column(String(100), nullable=False)
    # "고객PM", "고객실무", "승인자", "수행PM", "구축엔지니어", "유지보수담당", "보안업무담당"
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("project_customer_id", "contact_id", "project_role"),
    )

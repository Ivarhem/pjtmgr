from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class AssetContact(TimestampMixin, Base):
    __tablename__ = "asset_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    contact_id: Mapped[int] = mapped_column(
        ForeignKey("partner_contacts.id"), index=True
    )
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)

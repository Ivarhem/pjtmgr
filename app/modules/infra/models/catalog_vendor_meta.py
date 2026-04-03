from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class CatalogVendorMeta(TimestampMixin, Base):
    """제조사별 메타 정보 (한글명, 메모 등). vendor_canonical이 PK이자 식별자."""

    __tablename__ = "catalog_vendor_meta"

    vendor_canonical: Mapped[str] = mapped_column(
        String(100), primary_key=True, comment="대표 제조사명 (영문)"
    )
    name_ko: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="제조사명 (한글)"
    )
    memo: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="메모"
    )

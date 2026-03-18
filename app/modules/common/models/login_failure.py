"""로그인 실패 추적 모델."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LoginFailure(Base):
    __tablename__ = "login_failures"

    id: Mapped[int] = mapped_column(primary_key=True)
    login_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

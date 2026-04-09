"""감사 로그 (AuditLog) - 주요 데이터 변경 이력 기록."""
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)      # create / update / delete
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # contract / contract_period / transaction_line / receipt
    entity_id: Mapped[int | None] = mapped_column(Integer)
    module: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)  # "common", "accounting", "infra"
    summary: Mapped[str | None] = mapped_column(String(500))             # 변경 요약 (사람이 읽을 수 있는 형태)
    detail: Mapped[str | None] = mapped_column(Text)                     # JSON diff 등 상세 (향후 확장)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, index=True
    )

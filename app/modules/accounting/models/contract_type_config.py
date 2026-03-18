"""사업유형 설정 (ContractTypeConfig) - 관리자가 관리하는 사업유형 목록 + 기본값"""
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ContractTypeConfig(Base):
    __tablename__ = "contract_type_configs"

    code: Mapped[str] = mapped_column(String(30), primary_key=True)  # MA, SI, HW 등
    label: Mapped[str] = mapped_column(String(50), nullable=False)   # 표시명 (기본: code와 동일)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)      # 정렬 순서
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)   # 비활성화 시 새 사업에 사용 불가

    # ── 사업 생성 시 기본값 ─────────────────────────────────────────
    default_gp_pct: Mapped[int | None] = mapped_column(Integer)                     # 기본 GP% (정수, 예: 40 → 40%)
    default_inspection_day: Mapped[int | None] = mapped_column(Integer)             # 기본 검수일 (매월 N일, 0=말일)
    default_invoice_month_offset: Mapped[int | None] = mapped_column(Integer)       # 발행 기준월 (0=당월, 1=익월)
    default_invoice_day_type: Mapped[str | None] = mapped_column(String(20))        # 발행일 유형: 1일/말일/특정일
    default_invoice_day: Mapped[int | None] = mapped_column(Integer)                # 특정일인 경우 날짜
    default_invoice_holiday_adjust: Mapped[str | None] = mapped_column(String(10))  # 휴일 조정: 전/후

"""용어 설정 (TermConfig) - 관리자가 UI 표시 라벨을 커스터마이징할 수 있는 용어 사전"""
from sqlalchemy import String, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TermConfig(Base):
    __tablename__ = "term_configs"

    term_key: Mapped[str] = mapped_column(String(50), primary_key=True)          # 코드 내부 키 (예: contract, receipt)
    category: Mapped[str] = mapped_column(String(30), nullable=False)            # 그룹: entity, metric, report
    standard_label_en: Mapped[str] = mapped_column(String(100), nullable=False)  # 영문 표준명
    standard_label_ko: Mapped[str] = mapped_column(String(100), nullable=False)  # 한글 표준명
    definition: Mapped[str | None] = mapped_column(Text)                         # 용어 정의/설명
    default_ui_label: Mapped[str] = mapped_column(String(50), nullable=False)    # 기본 UI 표시명
    custom_ui_label: Mapped[str | None] = mapped_column(String(50))              # 관리자 커스텀 표시명
    is_customized: Mapped[bool] = mapped_column(Boolean, default=False)          # 커스텀 여부
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)               # 활성 여부
    sort_order: Mapped[int] = mapped_column(Integer, default=0)                  # 표시 순서

    @property
    def ui_label(self) -> str:
        """실제 UI에 표시할 라벨. 커스텀이 있으면 커스텀, 없으면 기본값."""
        if self.is_customized and self.custom_ui_label:
            return self.custom_ui_label
        return self.default_ui_label

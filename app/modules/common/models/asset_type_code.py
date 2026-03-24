"""자산유형 코드 설정 (AssetTypeCode) - 관리자가 관리하는 자산유형 목록."""
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AssetTypeCode(Base):
    __tablename__ = "asset_type_codes"

    type_key: Mapped[str] = mapped_column(String(30), primary_key=True)   # server, network 등
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)  # SVR, NET 등
    label: Mapped[str] = mapped_column(String(50), nullable=False)        # 서버, 네트워크 등
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

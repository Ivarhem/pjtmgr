"""DB 스키마 준비 및 레거시 마이그레이션 초기화."""
from __future__ import annotations

from app.config import ENV
from app.database import Base, engine
from app.migrations_legacy import run_migrations


def prepare_database() -> None:
    """현재 환경에 맞게 스키마를 준비하고 레거시 마이그레이션을 적용한다."""
    if ENV == "dev":
        Base.metadata.create_all(bind=engine)
    run_migrations()

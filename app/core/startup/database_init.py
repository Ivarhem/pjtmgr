"""DB 스키마 준비 및 레거시 마이그레이션 초기화."""
from __future__ import annotations

import logging
import os

from sqlalchemy import inspect

from app.core.config import ENV
from app.core.database import Base, engine

logger = logging.getLogger(__name__)


def _get_alembic_config():
    """Alembic Config 객체를 생성한다."""
    from alembic.config import Config

    # 프로젝트 루트의 alembic.ini를 찾는다 (app/core/startup/ → 3단계 상위)
    ini_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "alembic.ini")
    ini_path = os.path.normpath(ini_path)
    cfg = Config(ini_path)
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    return cfg


def _apply_alembic() -> None:
    """Alembic 버전 테이블 존재 여부와 무관하게 upgrade를 적용한다."""
    from alembic import command

    cfg = _get_alembic_config()
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        logger.info("Alembic 초기 upgrade 실행 (head)")
        command.upgrade(cfg, "head")
    else:
        logger.info("Alembic upgrade 실행 (head)")
        command.upgrade(cfg, "head")


def prepare_database() -> None:
    """현재 환경에 맞게 스키마를 준비하고 레거시 마이그레이션을 적용한다."""
    if ENV == "dev":
        Base.metadata.create_all(bind=engine)
    # Docker 환경에서는 entrypoint의 `alembic upgrade head`가 이미 실행됨.
    # 중복 실행 시 advisory lock 충돌 방지를 위해 SKIP_LIFESPAN_ALEMBIC 환경변수로 제어.
    if not os.getenv("SKIP_LIFESPAN_ALEMBIC"):
        _apply_alembic()

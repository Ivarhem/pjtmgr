"""DB 스키마 준비 및 레거시 마이그레이션 초기화."""
from __future__ import annotations

import logging
import os

from sqlalchemy import inspect

from app.config import ENV
from app.database import Base, engine
from app.migrations_legacy import run_migrations

logger = logging.getLogger(__name__)


def _get_alembic_config():
    """Alembic Config 객체를 생성한다."""
    from alembic.config import Config

    ini_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
    ini_path = os.path.normpath(ini_path)
    cfg = Config(ini_path)
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    return cfg


def _apply_alembic() -> None:
    """Alembic 버전 테이블 존재 여부에 따라 stamp 또는 upgrade 수행."""
    from alembic import command

    cfg = _get_alembic_config()
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        logger.info("Alembic 초기 stamp 실행 (head)")
        command.stamp(cfg, "head")
    else:
        logger.info("Alembic upgrade 실행 (head)")
        command.upgrade(cfg, "head")


def prepare_database() -> None:
    """현재 환경에 맞게 스키마를 준비하고 레거시 마이그레이션을 적용한다."""
    if ENV == "dev":
        Base.metadata.create_all(bind=engine)
    run_migrations()
    _apply_alembic()

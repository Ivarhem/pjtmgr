"""FastAPI lifespan orchestration."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.startup.bootstrap import initialize_reference_data
from app.core.startup.database_init import prepare_database

logger = logging.getLogger("sales")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """앱 시작/종료 시 실행되는 생명주기 핸들러."""
    logger.info("영업관리 시스템 시작 (ENV=%s)", os.getenv("ENV", "dev"))
    prepare_database()
    initialize_reference_data()
    yield

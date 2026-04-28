"""FastAPI lifespan orchestration."""
from __future__ import annotations

import logging
import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.startup.bootstrap import initialize_reference_data
from app.core.startup.database_init import prepare_database
from app.core.startup.catalog_research_worker import (
    catalog_research_worker,
    should_run_catalog_research_worker,
)

logger = logging.getLogger("sales")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 생명주기 핸들러."""
    logger.info("영업관리 시스템 시작 (ENV=%s)", os.getenv("ENV", "dev"))
    prepare_database()
    initialize_reference_data()

    worker_task = None
    if should_run_catalog_research_worker():
        worker_task = asyncio.create_task(catalog_research_worker(), name="catalog-research-worker")
        app.state.catalog_research_worker = worker_task

    try:
        yield
    finally:
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

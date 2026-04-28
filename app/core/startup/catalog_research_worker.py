from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import select, text

from app.core.auth.authorization import can_manage_catalog_products
from app.core.database import SessionLocal
from app.modules.common.models.user import User
from app.modules.infra.services.catalog_research_service import batch_research_catalog_products

logger = logging.getLogger("sales")

_LOCK_KEY = int(os.getenv("CATALOG_RESEARCH_AUTO_LOCK_KEY") or "20260423")
_ENABLED = (os.getenv("CATALOG_RESEARCH_AUTO_ENABLED") or "true").strip().lower() not in {"0", "false", "no", "off"}
_RUN_EVERY_SECONDS = max(15, int(os.getenv("CATALOG_RESEARCH_AUTO_INTERVAL_SECONDS") or "45"))
_IDLE_SECONDS = max(_RUN_EVERY_SECONDS, int(os.getenv("CATALOG_RESEARCH_AUTO_IDLE_SECONDS") or "300"))


def _find_catalog_research_actor(db) -> User | None:
    for user in db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.id.asc())):
        if can_manage_catalog_products(user):
            return user
    return None


def _run_catalog_research_cycle() -> bool:
    db = SessionLocal()
    lock_acquired = False
    try:
        lock_acquired = bool(db.execute(text("select pg_try_advisory_lock(:key)"), {"key": _LOCK_KEY}).scalar())
        if not lock_acquired:
            return False

        actor = _find_catalog_research_actor(db)
        if actor is None:
            logger.warning("카탈로그 자동 deep research 실행 계정을 찾지 못했습니다.")
            return False

        result = batch_research_catalog_products(
            db,
            current_user=actor,
            limit=1,
            fill_only=True,
            force=False,
            include_pending_review=False,
        )
        row = (result.get("rows") or [None])[0]
        if result.get("selected", 0) > 0 and row:
            logger.info(
                "카탈로그 자동 deep research 처리: product_id=%s vendor=%s name=%s skipped=%s failed=%s",
                row.get("product_id"),
                row.get("vendor"),
                row.get("name"),
                row.get("skipped"),
                row.get("status") == "error",
            )
            return True
        return False
    except Exception:
        logger.exception("카탈로그 자동 deep research 처리 중 오류가 발생했습니다.")
        return False
    finally:
        try:
            if lock_acquired:
                db.execute(text("select pg_advisory_unlock(:key)"), {"key": _LOCK_KEY})
        except Exception:
            logger.exception("카탈로그 자동 deep research 락 해제에 실패했습니다.")
        db.close()


async def catalog_research_worker() -> None:
    logger.info(
        "카탈로그 자동 deep research 워커 시작 (enabled=%s, run_every=%ss, idle=%ss)",
        _ENABLED,
        _RUN_EVERY_SECONDS,
        _IDLE_SECONDS,
    )
    while True:
        processed = await asyncio.to_thread(_run_catalog_research_cycle)
        await asyncio.sleep(_RUN_EVERY_SECONDS if processed else _IDLE_SECONDS)


def should_run_catalog_research_worker() -> bool:
    return _ENABLED


def run_catalog_research_worker_forever() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("카탈로그 자동 deep research 전용 워커 프로세스 시작")
    asyncio.run(catalog_research_worker())


if __name__ == "__main__":
    run_catalog_research_worker_forever()

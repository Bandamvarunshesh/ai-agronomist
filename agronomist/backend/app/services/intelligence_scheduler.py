from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.intelligence_service import IntelligenceService


logger = logging.getLogger(__name__)


class IntelligenceScheduler:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if not settings.intelligence_sync_enabled:
            logger.info("Agricultural intelligence sync scheduler disabled")
            return
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())
            logger.info("Agricultural intelligence sync scheduler started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            await self._task

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.to_thread(self._sync_once)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=settings.intelligence_sync_interval_seconds,
                )
            except asyncio.TimeoutError:
                continue

    def _sync_once(self) -> None:
        db = SessionLocal()
        try:
            created_count = IntelligenceService(db).sync_all_sources()
            logger.info(
                "Agricultural intelligence sync complete: created_count=%s",
                created_count,
            )
        except Exception:
            logger.exception("Agricultural intelligence sync failed")
        finally:
            db.close()


intelligence_scheduler = IntelligenceScheduler()

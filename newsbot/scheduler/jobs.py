"""Schedule the daily digest job."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def create_scheduler(timezone: str) -> AsyncIOScheduler:
    """Create an AsyncIOScheduler configured for ``timezone``."""
    return AsyncIOScheduler(timezone=ZoneInfo(timezone))


def schedule_daily_digest(
    scheduler: AsyncIOScheduler,
    job: Callable[..., Any],
    *,
    hour: int = 8,
    minute: int = 30,
) -> None:
    """Register ``job`` as a cron trigger at hour:minute."""
    scheduler.add_job(
        job,
        trigger=CronTrigger(
            hour=hour,
            minute=minute,
            timezone=scheduler.timezone,
        ),
        id="daily_digest",
        name="run_daily_digest",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    logger.info("Scheduled daily digest at %02d:%02d (%s)", hour, minute, scheduler.timezone)


def scheduler_lifespan(scheduler: AsyncIOScheduler):
    """Build a FastAPI lifespan context that starts/stops ``scheduler``."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if not scheduler.running:
            scheduler.start()
            logger.info("APScheduler started")
        try:
            yield
        finally:
            if scheduler.running:
                scheduler.shutdown(wait=False)
                logger.info("APScheduler stopped")

    return lifespan


def attach_scheduler_to_app(app: Any, scheduler: AsyncIOScheduler) -> None:
    """Start/stop scheduler with the FastAPI app lifecycle."""
    app.router.lifespan_context = scheduler_lifespan(scheduler)

    # Keep startup/shutdown hooks for older test/runtime expectations
    def _start() -> None:
        if not scheduler.running:
            scheduler.start()

    def _stop() -> None:
        if scheduler.running:
            scheduler.shutdown(wait=False)

    app.router.on_startup.append(_start)
    app.router.on_shutdown.append(_stop)

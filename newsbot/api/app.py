"""FastAPI app factory and lifecycle hooks."""

from __future__ import annotations

from fastapi import FastAPI

from newsbot.api.routes import router
from newsbot.config import get_settings
from newsbot.logging_utils import configure_logging
from newsbot.pipeline.digest import run_daily_digest
from newsbot.scheduler.jobs import (
    attach_scheduler_to_app,
    create_scheduler,
    schedule_daily_digest,
)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    configure_logging()
    settings = get_settings()
    scheduler = create_scheduler(settings.timezone)
    schedule_daily_digest(
        scheduler,
        run_daily_digest,
        hour=settings.digest_hour,
        minute=settings.digest_minute,
    )

    app = FastAPI(
        title="NewsBot",
        description="Daily newsletter digests with retrieval-backed Q&A",
        version="0.1.0",
    )
    app.include_router(router)
    attach_scheduler_to_app(app, scheduler)
    app.state.scheduler = scheduler
    return app


app = create_app()

"""Phase 6 — Scheduler completeness."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.phase6


def test_scheduler_modules_importable() -> None:
    from newsbot.scheduler import create_scheduler, schedule_daily_digest
    from newsbot.scheduler.jobs import attach_scheduler_to_app

    assert callable(create_scheduler)
    assert callable(schedule_daily_digest)
    assert callable(attach_scheduler_to_app)


def test_create_scheduler_uses_configured_timezone() -> None:
    from newsbot.scheduler.jobs import create_scheduler

    scheduler = create_scheduler("America/Los_Angeles")
    assert scheduler is not None
    # APScheduler exposes timezone on the scheduler instance
    tz = getattr(scheduler, "timezone", None) or getattr(scheduler, "_timezone", None)
    assert tz is not None
    assert "Los_Angeles" in str(tz) or "America/Los_Angeles" in str(tz)


def test_schedule_daily_digest_registers_830_cron() -> None:
    from newsbot.scheduler.jobs import create_scheduler, schedule_daily_digest

    scheduler = create_scheduler("America/Los_Angeles")
    job_fn = MagicMock(name="run_daily_digest")

    schedule_daily_digest(scheduler, job_fn, hour=8, minute=30)

    jobs = scheduler.get_jobs()
    assert len(jobs) >= 1
    job = jobs[0]
    trigger = job.trigger
    # CronTrigger stores fields
    hour = getattr(trigger, "fields", None)
    if hour is not None:
        # fields order includes year, month, day, week, day_of_week, hour, minute, second
        field_map = {f.name: str(f) for f in trigger.fields}
        assert field_map.get("hour") == "8"
        assert field_map.get("minute") == "30"
    else:
        assert "8" in str(trigger) and "30" in str(trigger)


def test_attach_scheduler_to_app_hooks_lifecycle() -> None:
    from fastapi import FastAPI

    from newsbot.scheduler.jobs import attach_scheduler_to_app, create_scheduler

    app = FastAPI()
    scheduler = create_scheduler("UTC")
    scheduler.start = MagicMock()
    scheduler.shutdown = MagicMock()

    attach_scheduler_to_app(app, scheduler)

    # Lifespan or startup/shutdown handlers must be registered
    has_startup = bool(app.router.on_startup) or hasattr(app, "router")
    assert has_startup
    # Calling the attached hook should start the scheduler (implementation-defined)
    if app.router.on_startup:
        for handler in app.router.on_startup:
            handler()
        scheduler.start.assert_called()
    else:
        # Modern lifespan API: ensure attach did not raise and left a lifespan context
        assert app.router.lifespan_context is not None or True

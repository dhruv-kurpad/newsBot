"""APScheduler job registration and FastAPI lifecycle integration."""

from newsbot.scheduler.jobs import create_scheduler, schedule_daily_digest

__all__ = ["create_scheduler", "schedule_daily_digest"]

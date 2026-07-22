"""Run API (with scheduler) and Telegram poller together."""

from __future__ import annotations

import asyncio
import logging
import threading

import uvicorn

from newsbot.logging_utils import configure_logging
from newsbot.telegram.runner import build_bot, poll_updates


def _run_api() -> None:
    uvicorn.run(
        "newsbot.api.app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


def main() -> None:
    configure_logging()
    logger = logging.getLogger("newsbot")
    logger.info("Starting NewsBot API + Telegram poller")

    api_thread = threading.Thread(target=_run_api, name="uvicorn", daemon=True)
    api_thread.start()

    bot = build_bot()
    asyncio.run(poll_updates(bot))


if __name__ == "__main__":
    main()

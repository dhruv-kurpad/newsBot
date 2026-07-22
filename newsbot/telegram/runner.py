"""Long-polling runner for Telegram updates."""

from __future__ import annotations

import asyncio
import logging

import httpx

from newsbot.config import get_settings
from newsbot.pipeline.digest import answer_question, run_daily_digest
from newsbot.telegram.bot import NewsBot

logger = logging.getLogger(__name__)


def build_bot() -> NewsBot:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in .env"
        )
    return NewsBot(
        token=settings.telegram_bot_token,
        chat_id=str(settings.telegram_chat_id),
        ask_handler=answer_question,
        # Bot sends the formatted reply itself — avoid double-send from the pipeline
        digest_handler=lambda: run_daily_digest(send_telegram=False),
    )


async def poll_updates(bot: NewsBot, *, poll_timeout: int = 30) -> None:
    """Long-poll Telegram getUpdates and dispatch to the bot."""
    offset: int | None = None
    async with httpx.AsyncClient(timeout=poll_timeout + 10) as client:
        while True:
            params: dict[str, int] = {"timeout": poll_timeout}
            if offset is not None:
                params["offset"] = offset
            try:
                response = await client.get(bot._api_url("getUpdates"), params=params)
                response.raise_for_status()
                updates = response.json().get("result") or []
            except Exception:  # noqa: BLE001
                logger.exception("Telegram poll failed; retrying in 3s")
                await asyncio.sleep(3)
                continue

            for update in updates:
                offset = int(update["update_id"]) + 1
                try:
                    await bot.handle_update(update)
                except Exception:  # noqa: BLE001
                    logger.exception("Failed handling update %s", update.get("update_id"))


def main() -> None:
    from newsbot.logging_utils import configure_logging

    configure_logging()
    bot = build_bot()
    logger.info("Starting Telegram poller for chat_id=%s", bot.chat_id)
    asyncio.run(poll_updates(bot))


if __name__ == "__main__":
    main()

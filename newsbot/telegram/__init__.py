"""Telegram bot: digest delivery and follow-up Q&A."""

from newsbot.telegram.bot import NewsBot
from newsbot.telegram.format import format_daily_digest

__all__ = ["NewsBot", "format_daily_digest"]

"""Telegram bot wrapper for digests and follow-up questions."""

from __future__ import annotations

import logging
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 4096


class NewsBot:
    def __init__(
        self,
        token: str,
        chat_id: str,
        *,
        ask_handler: Callable[[str], str] | None = None,
        digest_handler: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.token = token
        self.chat_id = str(chat_id)
        self.ask_handler = ask_handler
        self.digest_handler = digest_handler

    def _api_url(self, method: str) -> str:
        return f"{TELEGRAM_API}/bot{self.token}/{method}"

    async def send_message(self, text: str, *, chat_id: str | None = None) -> None:
        """Send a text message to Telegram."""
        target = str(chat_id or self.chat_id)
        payload_text = text
        if len(payload_text) > MAX_MESSAGE_LENGTH:
            payload_text = payload_text[: MAX_MESSAGE_LENGTH - 20] + "\n…(truncated)"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._api_url("sendMessage"),
                json={
                    "chat_id": target,
                    "text": payload_text,
                    "disable_web_page_preview": True,
                },
            )
            response.raise_for_status()

    async def handle_update(self, update: dict[str, Any]) -> str | None:
        """Handle an incoming Telegram update; return reply text if any."""
        message = update.get("message") or update.get("edited_message") or {}
        text = (message.get("text") or "").strip()
        if not text:
            return None

        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if self.chat_id and chat_id and chat_id != self.chat_id:
            logger.info("Ignoring message from unauthorized chat_id=%s", chat_id)
            return None

        command = text.split()[0].split("@", 1)[0].lower()

        if command in {"/start", "/help"}:
            reply = (
                "NewsBot ready.\n"
                "• Send any question about your newsletter digests\n"
                "• /digest — run the daily digest now"
            )
            await self.send_message(reply, chat_id=chat_id or None)
            return reply

        if command == "/digest":
            reply = await self.handle_digest_command()
            return reply

        if not self.ask_handler:
            reply = "Ask handler is not configured."
            await self.send_message(reply, chat_id=chat_id or None)
            return reply

        reply = self.ask_handler(text)
        await self.send_message(reply, chat_id=chat_id or None)
        return reply

    async def handle_digest_command(self) -> str:
        """Optional /digest command to trigger a manual digest run."""
        if not self.digest_handler:
            reply = "Digest handler is not configured."
            await self.send_message(reply)
            return reply

        result = self.digest_handler()
        digest_text = (result.get("digest") or "").strip()
        count = int(result.get("count") or 0)
        status = result.get("status")

        if digest_text:
            reply = digest_text
        elif status == "empty" or count == 0:
            reply = "No new newsletters to digest right now."
        else:
            reply = f"Digest finished (status={status}, count={count})."

        errors = result.get("errors") or []
        if errors:
            reply += f"\n\nWarnings: {len(errors)} item(s) failed."

        await self.send_message(reply)
        return reply

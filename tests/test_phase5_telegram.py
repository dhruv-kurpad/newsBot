"""Phase 5 — Telegram bot completeness."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from newsbot.llm.summarizer import StructuredSummary

pytestmark = pytest.mark.phase5


def _summaries() -> list[StructuredSummary]:
    return [
        StructuredSummary(
            title="OpenAI releases new safety framework",
            summary="OpenAI published a new safety framework.",
            key_points=["Evaluation harness"],
            important_facts=[],
            why_it_matters="Sets industry expectations.",
            follow_up_questions=[],
            links=["https://openai.com/safety"],
            message_id="1",
        ),
        StructuredSummary(
            title="Anthropic expands Claude API",
            summary="Anthropic added API features.",
            key_points=["New endpoints"],
            important_facts=[],
            why_it_matters="Broader developer access.",
            follow_up_questions=[],
            links=[],
            message_id="2",
        ),
    ]


@pytest.fixture
def mock_telegram_http(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True, "result": {}}

    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.post = AsyncMock(return_value=mock_response)
    client.get = AsyncMock(return_value=mock_response)

    monkeypatch.setattr(
        "newsbot.telegram.bot.httpx.AsyncClient",
        lambda *args, **kwargs: client,
    )
    return client


def test_telegram_modules_importable() -> None:
    from newsbot.telegram import NewsBot, format_daily_digest

    assert NewsBot is not None
    assert callable(format_daily_digest)


def test_format_daily_digest_matches_spec_shape() -> None:
    from newsbot.telegram.format import format_daily_digest

    text = format_daily_digest(_summaries(), digest_date=date(2026, 7, 22))

    assert "Daily" in text and "Digest" in text
    assert "July 22" in text or "2026-07-22" in text or "Jul" in text
    assert "1." in text
    assert "OpenAI releases new safety framework" in text
    assert "Summary:" in text
    assert "Why it matters:" in text
    assert "2." in text
    assert "Anthropic expands Claude API" in text
    assert "Ask me" in text or "ask me" in text.lower()


@pytest.mark.asyncio
async def test_send_message_delivers_text(mock_telegram_http: AsyncMock) -> None:
    from newsbot.telegram.bot import NewsBot

    bot = NewsBot(token="TEST_TOKEN", chat_id="12345")
    await bot.send_message("hello digest")
    mock_telegram_http.post.assert_awaited()
    args, kwargs = mock_telegram_http.post.await_args
    assert "sendMessage" in args[0]
    assert kwargs["json"]["text"] == "hello digest"
    assert kwargs["json"]["chat_id"] == "12345"


@pytest.mark.asyncio
async def test_handle_update_routes_questions_to_ask_handler(
    mock_telegram_http: AsyncMock,
) -> None:
    from newsbot.telegram.bot import NewsBot

    ask = MagicMock(return_value="Here is more about item 2.")
    bot = NewsBot(token="TEST_TOKEN", chat_id="12345", ask_handler=ask)

    update = {
        "message": {
            "chat": {"id": 12345},
            "text": "Tell me more about item 2",
        }
    }

    reply = await bot.handle_update(update)
    ask.assert_called_once_with("Tell me more about item 2")
    assert reply is not None
    assert "item 2" in reply.lower() or "Here is more" in reply
    mock_telegram_http.post.assert_awaited()


@pytest.mark.asyncio
async def test_digest_command_triggers_handler(mock_telegram_http: AsyncMock) -> None:
    from newsbot.telegram.bot import NewsBot

    digest = MagicMock(return_value={"digest": "Daily AI News Digest — July 22", "count": 1})
    bot = NewsBot(token="TEST_TOKEN", chat_id="12345", digest_handler=digest)

    result = await bot.handle_digest_command()
    digest.assert_called_once()
    assert "Digest" in result or "digest" in result.lower()
    mock_telegram_http.post.assert_awaited()

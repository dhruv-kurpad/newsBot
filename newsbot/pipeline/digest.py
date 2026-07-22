"""Daily digest and Q&A orchestration."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Any

from newsbot.config import get_settings
from newsbot.gmail.client import get_gmail_service, list_new_messages
from newsbot.gmail.extract import extract_article
from newsbot.gmail.processed import ProcessedMessageStore
from newsbot.llm.client import LLMClient
from newsbot.llm.summarizer import StructuredSummary, summarize_article
from newsbot.logging_utils import safe_call
from newsbot.telegram.bot import NewsBot
from newsbot.telegram.format import format_daily_digest
from newsbot.vectorstore.store import VectorStore

logger = logging.getLogger(__name__)


def _send_digest_to_telegram(text: str) -> bool:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured; skipping digest send")
        return False

    bot = NewsBot(
        token=settings.telegram_bot_token,
        chat_id=str(settings.telegram_chat_id),
    )

    async def _send() -> None:
        await bot.send_message(text)

    try:
        try:
            asyncio.get_running_loop()
            in_running_loop = True
        except RuntimeError:
            in_running_loop = False

        if in_running_loop:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(lambda: asyncio.run(_send())).result()
        else:
            asyncio.run(_send())
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send Telegram digest")
        return False


def run_daily_digest(*, send_telegram: bool = True) -> dict[str, Any]:
    """Fetch → extract → summarize → store → format Telegram digest text."""
    settings = get_settings()
    errors: list[str] = []
    purged = 0

    vector_store = VectorStore(settings.vector_store_path)
    try:
        purged = vector_store.purge_older_than(settings.retention_days)
    except Exception as exc:  # noqa: BLE001 — retention failure shouldn't block digest
        logger.exception("Failed purging old summaries")
        errors.append(f"purge: {exc}")

    try:
        processed = ProcessedMessageStore(settings.processed_messages_path)
        service = get_gmail_service(
            settings.gmail_credentials_path,
            settings.gmail_token_path,
        )
        messages = list_new_messages(
            service,
            settings.gmail_label,
            processed_ids=processed.all_ids(),
        )
    except Exception as exc:  # noqa: BLE001 — Gmail/auth failures should not crash the app
        logger.exception("Gmail fetch failed")
        return {
            "status": "error",
            "count": 0,
            "digest": "",
            "sent": False,
            "purged": purged,
            "errors": errors + [f"gmail: {exc}"],
        }

    if not messages:
        logger.info("No new messages under label=%s", settings.gmail_label)
        return {
            "status": "empty",
            "count": 0,
            "digest": "",
            "sent": False,
            "purged": purged,
            "errors": errors,
        }

    llm = LLMClient(settings.llm_base_url, settings.llm_model)
    summaries: list[StructuredSummary] = []

    for message in messages:
        message_id = str(message.get("id", ""))
        try:
            article = extract_article(message)
            summary = summarize_article(
                llm,
                article.body,
                title=article.subject or article.body[:80],
                message_id=article.message_id or message_id,
                links=article.links,
            )
            vector_store.store_summary(summary)
            processed.mark_processed(article.message_id or message_id)
            summaries.append(summary)
        except Exception as exc:  # noqa: BLE001 — continue processing other messages
            logger.exception("Failed processing message %s", message_id)
            errors.append(f"{message_id}: {exc}")

    digest = format_daily_digest(summaries) if summaries else ""
    sent = False
    if send_telegram and digest:
        sent = _send_digest_to_telegram(digest)

    status = "ok" if summaries and not errors else ("partial" if summaries else "error")
    if not summaries and not errors:
        status = "empty"

    logger.info(
        "Daily digest complete status=%s count=%s sent=%s purged=%s errors=%s",
        status,
        len(summaries),
        sent,
        purged,
        len(errors),
    )
    return {
        "status": status,
        "count": len(summaries),
        "digest": digest,
        "sent": sent,
        "purged": purged,
        "errors": errors,
    }


def answer_question(question: str) -> str:
    """Embed question → retrieve summaries → LLM answer."""
    settings = get_settings()
    store = VectorStore(settings.vector_store_path)
    hits = store.search(question, top_k=5)

    if not hits:
        return "I don't have any stored newsletter summaries yet. Run the daily digest first."

    context_blocks = []
    for hit in hits:
        title = hit.metadata.get("title", "Untitled")
        context_blocks.append(f"[{title}]\n{hit.text}")
    context = "\n\n---\n\n".join(context_blocks)

    prompt = (
        "You answer follow-up questions about newsletter digests.\n"
        "Use only the context below. If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )
    client = LLMClient(settings.llm_base_url, settings.llm_model)
    answer = safe_call(
        client.generate,
        prompt,
        default=(
            "I found relevant newsletter context, but the local LLM timed out or failed. "
            "Please make sure Ollama is running and try again."
        ),
    )
    return answer

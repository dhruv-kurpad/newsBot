"""Phase 1 — Gmail ingestion completeness."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.phase1


def test_gmail_modules_importable() -> None:
    from newsbot.gmail import ProcessedMessageStore, extract_article, get_gmail_service, list_new_messages
    from newsbot.gmail.extract import Article, html_to_plain_text

    assert callable(get_gmail_service)
    assert callable(list_new_messages)
    assert callable(extract_article)
    assert callable(html_to_plain_text)
    assert ProcessedMessageStore is not None
    assert Article is not None


def test_html_to_plain_text_strips_tags_and_scripts(sample_html: str) -> None:
    from newsbot.gmail.extract import html_to_plain_text

    text = html_to_plain_text(sample_html)
    assert "OpenAI releases new safety framework" in text
    assert "safety" in text.lower() or "OpenAI" in text
    assert "<p>" not in text
    assert "<script>" not in text
    assert "alert(1)" not in text


def test_extract_article_captures_fields() -> None:
    from newsbot.gmail.extract import extract_article

    message = {
        "id": "msg-123",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Weekly AI Digest"},
                {"name": "Date", "value": "Tue, 22 Jul 2026 08:00:00 -0700"},
            ],
            "mimeType": "text/html",
            "body": {
                "data": None,
            },
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {
                        # base64url for: <p>Hello <a href="https://example.com">world</a></p>
                        "data": "PHA+SGVsbG8gPGEgaHJlZj0iaHR0cHM6Ly9leGFtcGxlLmNvbSI+d29ybGQ8L2E+PC9wPg==",
                    },
                }
            ],
        },
    }

    article = extract_article(message)
    assert article.message_id == "msg-123"
    assert article.subject == "Weekly AI Digest"
    assert article.date
    assert "Hello" in article.body or "world" in article.body.lower()
    assert any("example.com" in link for link in article.links)


def test_list_new_messages_filters_by_label_and_processed() -> None:
    from newsbot.gmail.client import list_new_messages

    service = MagicMock()
    listed = MagicMock()
    listed.execute.return_value = {
        "messages": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
    }
    fetched = MagicMock()
    fetched.execute.side_effect = [
        {"id": "a", "labelIds": ["Newsletters"]},
        {"id": "c", "labelIds": ["Newsletters"]},
    ]
    service.users.return_value.messages.return_value.list.return_value = listed
    service.users.return_value.messages.return_value.get.return_value = fetched

    messages = list_new_messages(
        service,
        "Newsletters",
        processed_ids={"b"},
    )

    assert isinstance(messages, list)
    ids = {m["id"] for m in messages}
    assert "b" not in ids
    assert ids <= {"a", "c"}


def test_processed_message_store_persists_ids(tmp_path: Path) -> None:
    from newsbot.gmail.processed import ProcessedMessageStore

    store = ProcessedMessageStore(tmp_path / "processed.json")
    assert store.is_processed("msg-1") is False
    store.mark_processed("msg-1")
    assert store.is_processed("msg-1") is True

    reloaded = ProcessedMessageStore(tmp_path / "processed.json")
    assert reloaded.is_processed("msg-1") is True
    assert "msg-1" in reloaded.all_ids()

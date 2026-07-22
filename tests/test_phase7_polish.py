"""Phase 7 — End-to-end + polish completeness."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.phase7


def test_readme_exists_with_setup_guidance(repo_root: Path) -> None:
    readme = repo_root / "README.md"
    assert readme.is_file(), "Phase 7 incomplete: README.md is missing"
    text = readme.read_text().lower()
    for needle in ("gmail", "telegram", "ollama", ".env"):
        assert needle in text, f"README should mention '{needle}'"


def test_logging_helpers_work(caplog: pytest.LogCaptureFixture) -> None:
    from newsbot.logging_utils import configure_logging, safe_call

    configure_logging()

    def boom() -> int:
        raise RuntimeError("LLM timeout")

    result = safe_call(boom, default=-1)
    assert result == -1


def test_safe_call_returns_value_on_success() -> None:
    from newsbot.logging_utils import safe_call

    assert safe_call(lambda: 42, default=0) == 42


def test_empty_inbox_digest_is_handled() -> None:
    from newsbot.pipeline.digest import run_daily_digest

    with (
        patch("newsbot.pipeline.digest.get_gmail_service", return_value=object()),
        patch("newsbot.pipeline.digest.list_new_messages", return_value=[]),
        patch("newsbot.pipeline.digest.summarize_article") as summarize,
        patch("newsbot.telegram.bot.NewsBot.send_message", create=True),
    ):
        result = run_daily_digest()

    summarize.assert_not_called()
    assert isinstance(result, dict)
    assert result.get("count", 0) == 0 or result.get("status") in {"ok", "empty"}


def test_pipeline_error_handling_does_not_crash_on_llm_failure() -> None:
    from newsbot.gmail.extract import Article
    from newsbot.pipeline.digest import run_daily_digest

    article = Article(
        message_id="msg-err",
        subject="Broken",
        date="2026-07-22",
        body="content",
        links=[],
    )

    with (
        patch("newsbot.pipeline.digest.get_gmail_service", return_value=object()),
        patch("newsbot.pipeline.digest.list_new_messages", return_value=[{"id": "msg-err"}]),
        patch("newsbot.pipeline.digest.extract_article", return_value=article),
        patch("newsbot.pipeline.digest.summarize_article", side_effect=TimeoutError("LLM timeout")),
        patch("newsbot.pipeline.digest.ProcessedMessageStore") as store_cls,
    ):
        store_cls.return_value.is_processed.return_value = False
        result = run_daily_digest()

    assert isinstance(result, dict)
    assert result.get("errors") or result.get("status") in {"ok", "partial", "error"}


def test_ask_flow_retrieval_then_llm() -> None:
    from newsbot.pipeline.digest import answer_question
    from newsbot.vectorstore.store import StoredSummary

    retrieved = [
        StoredSummary(
            id="doc-1",
            text="OpenAI released a safety framework with red-teaming.",
            metadata={"title": "OpenAI safety framework", "message_id": "1"},
            score=0.9,
        )
    ]

    with (
        patch("newsbot.pipeline.digest.VectorStore") as store_cls,
        patch("newsbot.pipeline.digest.LLMClient") as llm_cls,
    ):
        store_cls.return_value.search.return_value = retrieved
        llm_cls.return_value.generate.return_value = (
            "The article covers OpenAI's new safety framework and red-teaming."
        )
        answer = answer_question("Tell me more about the AI safety framework.")

    assert isinstance(answer, str)
    assert "safety" in answer.lower()
    store_cls.return_value.search.assert_called()
    llm_cls.return_value.generate.assert_called()


def test_dockerfile_optional(repo_root: Path) -> None:
    dockerfile = repo_root / "Dockerfile"
    compose = repo_root / "docker-compose.yml"
    # Optional: pass if either exists; otherwise xfail as advisory
    if not dockerfile.is_file() and not compose.is_file():
        pytest.xfail("Optional Phase 7: Dockerfile / compose not added yet")
    assert dockerfile.is_file() or compose.is_file()

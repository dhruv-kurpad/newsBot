"""Phase 2 — Local LLM summarizer completeness."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.phase2


def test_llm_modules_importable() -> None:
    from newsbot.llm import LLMClient, StructuredSummary, parse_summary, summarize_article
    from newsbot.llm.summarizer import SUMMARY_PROMPT, build_summary_prompt

    assert LLMClient is not None
    assert StructuredSummary is not None
    assert callable(parse_summary)
    assert callable(summarize_article)
    assert "{content}" in SUMMARY_PROMPT or "{content}" in build_summary_prompt("x")


def test_build_summary_prompt_includes_article_and_structure() -> None:
    from newsbot.llm.summarizer import build_summary_prompt

    prompt = build_summary_prompt("Article body about AI regulation.")
    assert "Summary" in prompt
    assert "Key points" in prompt
    assert "Important facts" in prompt
    assert "Why it matters" in prompt
    assert "Follow-up questions" in prompt
    assert "Article body about AI regulation." in prompt


def test_parse_summary_returns_structured_fields(sample_summary_raw: str) -> None:
    from newsbot.llm.summarizer import parse_summary

    parsed = parse_summary(
        sample_summary_raw,
        title="OpenAI safety framework",
        message_id="msg-9",
    )
    assert parsed.title == "OpenAI safety framework"
    assert parsed.message_id == "msg-9"
    assert parsed.summary
    assert isinstance(parsed.key_points, list) and len(parsed.key_points) >= 1
    assert isinstance(parsed.important_facts, list) and len(parsed.important_facts) >= 1
    assert parsed.why_it_matters
    assert isinstance(parsed.follow_up_questions, list) and len(parsed.follow_up_questions) >= 1


def test_llm_client_generate_posts_to_local_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    import newsbot.llm.client as client_mod
    from newsbot.llm.client import LLMClient

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"response": "hello from model"}

    mock_httpx = MagicMock()
    mock_httpx.post.return_value = mock_response
    monkeypatch.setattr(client_mod, "httpx", mock_httpx, raising=False)

    client = LLMClient(base_url="http://localhost:11434", model="llama3.2")
    try:
        result = client.generate("Say hello")
    except NotImplementedError:
        pytest.fail("Phase 2 incomplete: LLMClient.generate is not implemented")

    assert isinstance(result, str)
    assert result.strip()


def test_summarize_article_uses_client_and_parser(sample_summary_raw: str) -> None:
    from newsbot.llm.client import LLMClient
    from newsbot.llm.summarizer import summarize_article

    client = MagicMock(spec=LLMClient)
    client.generate.return_value = sample_summary_raw

    summary = summarize_article(
        client,
        "Full newsletter article text…",
        title="OpenAI safety framework",
        message_id="msg-9",
        links=["https://openai.com/safety"],
    )

    client.generate.assert_called_once()
    assert summary.title == "OpenAI safety framework"
    assert summary.message_id == "msg-9"
    assert summary.summary
    assert summary.why_it_matters
    assert summary.links == ["https://openai.com/safety"]

"""Phase 3 — Vector store completeness."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from newsbot.llm.summarizer import StructuredSummary

pytestmark = pytest.mark.phase3


def _sample_summary(message_id: str = "msg-1") -> StructuredSummary:
    return StructuredSummary(
        title="OpenAI releases new safety framework",
        summary="OpenAI published a new safety framework.",
        key_points=["Evaluation harness", "Red teaming"],
        important_facts=["Announced July 2026"],
        why_it_matters="Sets industry expectations.",
        follow_up_questions=["What does the harness cover?"],
        links=["https://openai.com/safety"],
        message_id=message_id,
    )


def test_vectorstore_modules_importable() -> None:
    from newsbot.vectorstore import VectorStore, embed_text

    assert VectorStore is not None
    assert callable(embed_text)


def test_embed_text_returns_non_empty_vector() -> None:
    from newsbot.vectorstore.store import embed_text

    vector = embed_text(
        "AI regulation news",
        model="nomic-embed-text",
        base_url="http://localhost:11434",
    )
    assert isinstance(vector, list)
    assert len(vector) > 0
    assert all(isinstance(x, (int, float)) for x in vector)


def test_store_summary_persists_and_returns_id(tmp_path: Path) -> None:
    from newsbot.vectorstore.store import VectorStore

    fake_embedding = [0.1, 0.2, 0.3]

    with patch("newsbot.vectorstore.store.embed_text", return_value=fake_embedding):
        store = VectorStore(tmp_path / "chroma")
        doc_id = store.store_summary(_sample_summary())

    assert isinstance(doc_id, str)
    assert doc_id


def test_search_returns_relevant_summaries(tmp_path: Path) -> None:
    from newsbot.vectorstore.store import VectorStore

    fake_embedding = [0.1, 0.2, 0.3]

    with patch("newsbot.vectorstore.store.embed_text", return_value=fake_embedding):
        store = VectorStore(tmp_path / "chroma")
        store.store_summary(_sample_summary("msg-1"))
        store.store_summary(
            StructuredSummary(
                title="Anthropic expands Claude API",
                summary="Anthropic added new API features.",
                key_points=["New endpoints"],
                important_facts=[],
                why_it_matters="Broader developer access.",
                follow_up_questions=[],
                links=[],
                message_id="msg-2",
            )
        )
        results = store.search("Tell me more about the AI safety framework", top_k=2)

    assert isinstance(results, list)
    assert len(results) >= 1
    assert results[0].text or results[0].metadata
    assert results[0].metadata.get("message_id") or results[0].id


def test_purge_older_than_removes_stale_summaries(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    from newsbot.vectorstore.store import VectorStore

    fake_embedding = [0.1, 0.2, 0.3]

    with patch("newsbot.vectorstore.store.embed_text", return_value=fake_embedding):
        store = VectorStore(tmp_path / "chroma")
        store.store_summary(_sample_summary("keep-me"))
        store.store_summary(_sample_summary("drop-me"))

        collection = store._get_collection()
        old_ts = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
        collection.update(ids=["drop-me"], metadatas=[{"title": "old", "message_id": "drop-me", "stored_at": old_ts}])

        removed = store.purge_older_than(5)

    assert removed == 1
    remaining = store._get_collection().get(include=["metadatas"])
    assert "drop-me" not in remaining["ids"]
    assert "keep-me" in remaining["ids"]

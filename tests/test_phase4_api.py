"""Phase 4 — FastAPI backend completeness."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.phase4


def test_pipeline_modules_importable() -> None:
    from newsbot.pipeline import answer_question, run_daily_digest

    assert callable(run_daily_digest)
    assert callable(answer_question)


def test_create_app_exposes_required_routes() -> None:
    from newsbot.api.app import create_app

    app = create_app()
    client = TestClient(app)

    paths = set(app.openapi()["paths"])
    for required in ("/health", "/store-summary", "/daily-digest", "/ask"):
        assert required in paths, f"Missing route: {required}"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json().get("status") in {"ok", "healthy", "UP", "up"}


def test_store_summary_endpoint() -> None:
    from newsbot.api.app import create_app

    app = create_app()
    client = TestClient(app)

    payload = {
        "title": "OpenAI safety framework",
        "summary": "A new safety framework was released.",
        "key_points": ["evals"],
        "important_facts": ["2026"],
        "why_it_matters": "Industry norms",
        "follow_up_questions": ["What is covered?"],
        "links": ["https://openai.com/safety"],
        "message_id": "msg-1",
    }

    with patch("newsbot.api.routes.VectorStore") as mock_store_cls:
        mock_store_cls.return_value.store_summary.return_value = "doc-1"
        response = client.post("/store-summary", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body.get("id") or body.get("status") in {"ok", "stored"}


def test_daily_digest_endpoint_runs_pipeline() -> None:
    from newsbot.api.app import create_app

    app = create_app()
    client = TestClient(app)

    with patch(
        "newsbot.api.routes.run_daily_digest",
        return_value={"sent": True, "count": 2, "digest": "Daily AI News Digest"},
    ) as mocked:
        response = client.post("/daily-digest")

    assert response.status_code == 200
    mocked.assert_called_once()
    body = response.json()
    assert body.get("sent") is True or "digest" in body or body.get("status") == "ok"


def test_ask_endpoint_answers_from_retrieval() -> None:
    from newsbot.api.app import create_app

    app = create_app()
    client = TestClient(app)

    with patch(
        "newsbot.api.routes.answer_question",
        return_value="The safety framework adds external red-teaming.",
    ) as mocked:
        response = client.post("/ask", json={"question": "Tell me more about item 1"})

    assert response.status_code == 200
    mocked.assert_called_once()
    body = response.json()
    assert "answer" in body or "The safety framework" in str(body)


def test_run_daily_digest_orchestration_contract() -> None:
    from newsbot.pipeline.digest import run_daily_digest

    with (
        patch("newsbot.pipeline.digest.list_new_messages", return_value=[]),
        patch("newsbot.pipeline.digest.get_gmail_service", return_value=object()),
    ):
        result = run_daily_digest()

    assert isinstance(result, dict)
    # Empty inbox is a valid completed run
    assert "count" in result or "digest" in result or result.get("status") in {"ok", "empty"}

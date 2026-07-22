"""Shared fixtures and helpers for phase completeness tests."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def sample_html() -> str:
    return (
        "<html><body>"
        "<h1>OpenAI releases new safety framework</h1>"
        "<p>OpenAI published a <a href='https://openai.com/safety'>safety</a> update.</p>"
        "<script>alert(1)</script>"
        "</body></html>"
    )


@pytest.fixture
def sample_summary_raw() -> str:
    return """
Summary: OpenAI released a new safety framework for frontier models.
Key points:
- New evaluation harness
- External red-teaming requirements
Important facts:
- Announced July 2026
Why it matters: Sets industry expectations for model releases.
Follow-up questions you can ask me:
- What does the evaluation harness cover?
- How does this compare to Anthropic's approach?
""".strip()

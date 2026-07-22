"""HTTP client for a local LLM (Ollama, LM Studio, etc.)."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str) -> str:
        """Send ``prompt`` to the local model and return raw text."""
        # Prefer Ollama /api/generate; fall back to OpenAI-compatible /v1/chat/completions
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response")
            if isinstance(text, str) and text.strip():
                return text.strip()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ollama /api/generate failed: %s", exc)

        response = httpx.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("LLM returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("LLM returned empty content")
        return content.strip()

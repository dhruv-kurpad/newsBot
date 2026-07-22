"""Application settings loaded from environment and ``creds.json``."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

CREDS_PATH = Path("creds.json")


def load_creds(path: str | Path | None = None) -> dict[str, Any]:
    """Load secrets / Gmail service-account info from ``creds.json``."""
    creds_file = Path(path) if path else CREDS_PATH
    if not creds_file.is_file():
        return {}
    with creds_file.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Prefer OAuth client secrets + token (see gmail_auth.py)
    gmail_credentials_path: str = "credentials.json"
    gmail_token_path: str = "token.json"
    gmail_label: str = "Newsletters"
    gmail_user: str = ""  # mailbox to impersonate (domain-wide delegation)

    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2"

    embedding_model: str = "nomic-embed-text"
    vector_store_path: str = "./data/chroma"
    retention_days: int = 5

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    timezone: str = "America/Los_Angeles"
    digest_hour: int = 8
    digest_minute: int = 30

    processed_messages_path: str = "./data/processed_messages.json"

    def apply_creds_file(self, creds: dict[str, Any] | None = None) -> Settings:
        """Overlay Gmail-related fields from ``creds.json`` when present."""
        data = creds if creds is not None else load_creds(self.gmail_credentials_path)
        updates: dict[str, Any] = {}

        if data.get("gmail_label"):
            updates["gmail_label"] = str(data["gmail_label"])
        subject = data.get("gmail_user") or data.get("delegated_user") or data.get("subject")
        if subject:
            updates["gmail_user"] = str(subject)
        if data.get("telegram_bot_token"):
            updates["telegram_bot_token"] = str(data["telegram_bot_token"])
        if data.get("telegram_chat_id"):
            updates["telegram_chat_id"] = str(data["telegram_chat_id"])
        if data.get("llm_base_url"):
            updates["llm_base_url"] = str(data["llm_base_url"])
        if data.get("llm_model"):
            updates["llm_model"] = str(data["llm_model"])
        if data.get("timezone"):
            updates["timezone"] = str(data["timezone"])

        if not updates:
            return self
        return self.model_copy(update=updates)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    return settings.apply_creds_file()

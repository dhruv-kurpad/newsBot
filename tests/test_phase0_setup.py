"""Phase 0 — Project setup completeness."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.phase0

REQUIRED_ENV_KEYS = {
    "GMAIL_CREDENTIALS_PATH",
    "GMAIL_TOKEN_PATH",
    "GMAIL_LABEL",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TIMEZONE",
}


def test_requirements_file_exists(repo_root: Path) -> None:
    assert (repo_root / "requirements.txt").is_file() or (repo_root / "pyproject.toml").is_file()


def test_gitignore_exists(repo_root: Path) -> None:
    gitignore = repo_root / ".gitignore"
    assert gitignore.is_file()
    text = gitignore.read_text()
    assert ".env" in text
    assert "__pycache__" in text or "*.pyc" in text


def test_env_example_exists_with_required_keys(repo_root: Path) -> None:
    env_example = repo_root / ".env.example"
    assert env_example.is_file()
    text = env_example.read_text()
    missing = [key for key in REQUIRED_ENV_KEYS if key not in text]
    assert not missing, f".env.example missing keys: {missing}"


def test_config_module_exports_settings() -> None:
    from newsbot.config import Settings, get_settings

    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.gmail_label
    assert settings.llm_base_url
    assert settings.timezone
    assert isinstance(settings.digest_hour, int)
    assert isinstance(settings.digest_minute, int)


def test_settings_include_integration_fields() -> None:
    from newsbot.config import Settings

    fields = set(Settings.model_fields)
    expected = {
        "gmail_credentials_path",
        "gmail_token_path",
        "gmail_label",
        "llm_base_url",
        "llm_model",
        "telegram_bot_token",
        "telegram_chat_id",
        "timezone",
        "vector_store_path",
    }
    missing = expected - fields
    assert not missing, f"Settings missing fields: {missing}"

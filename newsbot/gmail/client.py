"""Gmail API client (OAuth via credentials.json/token.json, or service account)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from newsbot.gmail.auth import SCOPES, run_oauth


def _load_creds_info(credentials_path: str | Path) -> dict[str, Any]:
    path = Path(credentials_path)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def get_gmail_service(
    credentials_path: str,
    token_path: str,
) -> Any:
    """Return an authenticated Gmail API service (read-only).

    Supports:
    - OAuth desktop client ``credentials.json`` + persisted ``token.json``
      (create/refresh with ``python gmail_auth.py``)
    - Service account JSON, optionally with domain-wide delegation via
      ``gmail_user`` / ``delegated_user`` / ``subject`` in the file
    """
    info = _load_creds_info(credentials_path)

    if info.get("type") == "service_account":
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES,
        )
        subject = (
            info.get("gmail_user")
            or info.get("delegated_user")
            or info.get("subject")
        )
        if subject:
            creds = creds.with_subject(subject)
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    return run_oauth(credentials_path=credentials_path, token_path=token_path)


def list_new_messages(
    service: Any,
    label: str,
    *,
    processed_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """List new messages under ``label``, excluding already-processed IDs."""
    skip = processed_ids or set()
    query = f"label:{label}"

    message_refs: list[dict[str, str]] = []
    page_token: str | None = None
    while True:
        request_kwargs: dict[str, Any] = {
            "userId": "me",
            "q": query,
            "maxResults": 100,
        }
        if page_token:
            request_kwargs["pageToken"] = page_token

        response = service.users().messages().list(**request_kwargs).execute()
        message_refs.extend(response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    results: list[dict[str, Any]] = []
    for ref in message_refs:
        message_id = ref["id"]
        if message_id in skip:
            continue
        full = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        results.append(full)

    return results

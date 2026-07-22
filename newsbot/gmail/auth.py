"""Gmail OAuth helpers: credentials.json → token.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DEFAULT_CREDENTIALS = "credentials.json"
DEFAULT_TOKEN = "token.json"


def run_oauth(
    credentials_path: str | Path = DEFAULT_CREDENTIALS,
    token_path: str | Path = DEFAULT_TOKEN,
) -> Any:
    """Authorize Gmail read-only access and persist ``token.json``."""
    credentials_file = Path(credentials_path)
    token_file = Path(token_path)

    if not credentials_file.is_file():
        raise FileNotFoundError(
            f"Missing OAuth client file: {credentials_file.resolve()}\n"
            "Download the Desktop OAuth client JSON from Google Cloud Console "
            "and save it as credentials.json."
        )

    creds: Credentials | None = None
    if token_file.is_file():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_file),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        token_file.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds, cache_discovery=False)

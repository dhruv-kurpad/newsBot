#!/usr/bin/env python3
"""One-time (or refresh) Gmail OAuth helper.

Reads Google OAuth client secrets from ``credentials.json`` and writes
``token.json`` for reuse by the NewsBot Gmail client.

Usage:
    python gmail_auth.py
    python gmail_auth.py --credentials credentials.json --token token.json
"""

from __future__ import annotations

import argparse
import sys

from newsbot.gmail.auth import (
    DEFAULT_CREDENTIALS,
    DEFAULT_TOKEN,
    run_oauth,
)


def get_gmail_service(
    credentials_path: str = DEFAULT_CREDENTIALS,
    token_path: str = DEFAULT_TOKEN,
):
    """Compatibility wrapper for scripts."""
    return run_oauth(credentials_path=credentials_path, token_path=token_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Authorize Gmail and create token.json from credentials.json",
    )
    parser.add_argument(
        "--credentials",
        default=DEFAULT_CREDENTIALS,
        help=f"OAuth client secrets JSON (default: {DEFAULT_CREDENTIALS})",
    )
    parser.add_argument(
        "--token",
        default=DEFAULT_TOKEN,
        help=f"Output token path (default: {DEFAULT_TOKEN})",
    )
    args = parser.parse_args(argv)

    try:
        service = run_oauth(args.credentials, args.token)
        profile = service.users().getProfile(userId="me").execute()
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(
            f"Invalid credentials file: {exc}\n"
            "Use a Desktop/Web OAuth client JSON (not a service account).",
            file=sys.stderr,
        )
        return 1

    email = profile.get("emailAddress", "unknown")
    print(f"OAuth complete — {args.token} created/updated for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

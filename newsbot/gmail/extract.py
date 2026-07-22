"""Extract plain-text article content from Gmail message payloads."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Any
from bs4 import BeautifulSoup


@dataclass
class Article:
    message_id: str
    subject: str
    date: str
    body: str
    links: list[str] = field(default_factory=list)


def _decode_b64url(data: str | None) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode(
        "utf-8",
        errors="replace",
    )


def html_to_plain_text(html: str) -> str:
    """Convert HTML email body to plain text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse excessive blank lines / whitespace
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    compact = "\n".join(line for line in lines if line)
    return compact.strip()


def _header_map(payload: dict[str, Any]) -> dict[str, str]:
    headers = payload.get("headers") or []
    return {
        str(h.get("name", "")).lower(): str(h.get("value", ""))
        for h in headers
        if isinstance(h, dict)
    }


def _walk_parts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = [payload]
    stack = list(payload.get("parts") or [])
    while stack:
        part = stack.pop()
        parts.append(part)
        stack.extend(part.get("parts") or [])
    return parts


def _extract_html_and_text(payload: dict[str, Any]) -> tuple[str, str]:
    html_chunks: list[str] = []
    text_chunks: list[str] = []

    for part in _walk_parts(payload):
        mime = (part.get("mimeType") or "").lower()
        data = (part.get("body") or {}).get("data")
        if not data:
            continue
        decoded = _decode_b64url(data)
        if mime == "text/html":
            html_chunks.append(decoded)
        elif mime == "text/plain":
            text_chunks.append(decoded)
        elif not mime and decoded:
            # Top-level body without explicit mime
            if "<" in decoded and ">" in decoded:
                html_chunks.append(decoded)
            else:
                text_chunks.append(decoded)

    return "\n".join(html_chunks), "\n".join(text_chunks)


def _extract_links(html: str) -> list[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        # Normalize relative links poorly; keep absolute-ish URLs
        if href.startswith("//"):
            href = "https:" + href
        if href not in seen:
            seen.add(href)
            links.append(href)
    return links


def extract_article(message: dict[str, Any]) -> Article:
    """Extract subject, date, links, and body from a Gmail message resource."""
    payload = message.get("payload") or {}
    headers = _header_map(payload)
    html, plain = _extract_html_and_text(payload)

    if html:
        body = html_to_plain_text(html)
        links = _extract_links(html)
    else:
        body = plain.strip()
        links = list(dict.fromkeys(re.findall(r"https?://\S+", body)))

    return Article(
        message_id=str(message.get("id", "")),
        subject=headers.get("subject", ""),
        date=headers.get("date", ""),
        body=body,
        links=links,
    )

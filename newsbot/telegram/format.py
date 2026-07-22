"""Format daily digest Telegram messages."""

from __future__ import annotations

from datetime import date

from newsbot.llm.summarizer import StructuredSummary


def _format_day(digest_date: date) -> str:
    try:
        return digest_date.strftime("%B %-d")
    except ValueError:
        return digest_date.strftime("%B %d").replace(" 0", " ")


def format_daily_digest(
    summaries: list[StructuredSummary],
    *,
    digest_date: date | None = None,
) -> str:
    """Format summaries into the Daily AI News Digest Telegram message."""
    day = digest_date or date.today()
    lines = [f"Daily AI News Digest — {_format_day(day)}", ""]

    if not summaries:
        lines.append("No new newsletter articles today.")
        lines.append("")
        lines.append('Ask me: "Tell me more about item 2" or ask about any topic above.')
        return "\n".join(lines).strip()

    for index, item in enumerate(summaries, start=1):
        lines.append(f"{index}. {item.title or 'Untitled'}")
        lines.append(f"   Summary: {item.summary}")
        if item.why_it_matters:
            lines.append(f"   Why it matters: {item.why_it_matters}")
        if item.key_points:
            lines.append(f"   Key points: {'; '.join(item.key_points)}")
        if item.links:
            lines.append(f"   Link: {item.links[0]}")
        lines.append("")

    lines.append(
        'Ask me: "Tell me more about item 2" or "Explain the safety framework."'
    )
    return "\n".join(lines).strip()

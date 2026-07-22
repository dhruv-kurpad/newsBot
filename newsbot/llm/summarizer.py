"""Summarize newsletter articles with a structured prompt."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from newsbot.llm.client import LLMClient

SUMMARY_PROMPT = """Summarize the following newsletter article into:
- Summary
- Key points
- Important facts
- Why it matters
- Follow-up questions you can ask me

Article:
{content}
"""


@dataclass
class StructuredSummary:
    title: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    important_facts: list[str] = field(default_factory=list)
    why_it_matters: str = ""
    follow_up_questions: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    message_id: str = ""


def build_summary_prompt(content: str) -> str:
    return SUMMARY_PROMPT.format(content=content)


def _section_body(raw: str, header: str) -> str:
    pattern = re.compile(
        rf"(?im)^\s*(?:[-*]\s*)?{re.escape(header)}\s*:?\s*(.*?)(?=^\s*(?:[-*]\s*)?(?:Summary|Key points|Important facts|Why it matters|Follow-up questions)\b|\Z)",
        re.DOTALL,
    )
    match = pattern.search(raw)
    return match.group(1).strip() if match else ""


def _bullet_lines(body: str) -> list[str]:
    lines: list[str] = []
    for line in body.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+\.)\s*", "", line).strip()
        if cleaned:
            lines.append(cleaned)
    if lines:
        return lines
    compact = body.strip()
    return [compact] if compact else []


def parse_summary(raw: str, *, title: str = "", message_id: str = "") -> StructuredSummary:
    """Normalize raw LLM output into a StructuredSummary."""
    summary = _section_body(raw, "Summary")
    key_points = _bullet_lines(_section_body(raw, "Key points"))
    important_facts = _bullet_lines(_section_body(raw, "Important facts"))
    why_it_matters = _section_body(raw, "Why it matters")
    follow_ups = _bullet_lines(_section_body(raw, "Follow-up questions you can ask me"))
    if not follow_ups:
        follow_ups = _bullet_lines(_section_body(raw, "Follow-up questions"))

    if not summary:
        # Fallback: take the first non-empty paragraph
        for block in re.split(r"\n\s*\n", raw.strip()):
            if block.strip():
                summary = block.strip()
                break

    return StructuredSummary(
        title=title,
        summary=summary,
        key_points=key_points,
        important_facts=important_facts,
        why_it_matters=why_it_matters,
        follow_up_questions=follow_ups,
        message_id=message_id,
    )


def summarize_article(
    client: LLMClient,
    content: str,
    *,
    title: str = "",
    message_id: str = "",
    links: list[str] | None = None,
) -> StructuredSummary:
    """Summarize article content via the local LLM."""
    raw = client.generate(build_summary_prompt(content))
    parsed = parse_summary(raw, title=title, message_id=message_id)
    parsed.links = list(links or [])
    return parsed

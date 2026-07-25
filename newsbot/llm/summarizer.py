"""Summarize newsletter articles with a structured prompt."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from newsbot.llm.client import LLMClient

SUMMARY_PROMPT = """Summarize the following newsletter article.
Use these exact plain section headers (no markdown bold or bullets on the headers):

Summary:
Key points:
Important facts:
Why it matters:
Follow-up questions you can ask me:

Under Key points, Important facts, and Follow-up questions, use bullet lines starting with "- ".

Article:
{content}
"""

_SECTION_HEADERS = (
    "Summary",
    "Key points",
    "Important facts",
    "Why it matters",
    "Follow-up questions you can ask me",
    "Follow-up questions",
)

# Matches labels like: Summary: | - Summary | **Summary:** | ## Summary
_HEADER_DECORATION = r"(?:#{1,6}\s+|[-*]\s+)?(?:\*\*|__)?"
_HEADER_CLOSE = r"(?:\*\*|__)?"


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


def _section_header_re(header: str) -> str:
    return rf"{_HEADER_DECORATION}{re.escape(header)}:?{_HEADER_CLOSE}\s*:?\s*"


def _section_body(raw: str, header: str) -> str:
    next_headers = "|".join(re.escape(name) for name in _SECTION_HEADERS)
    pattern = re.compile(
        rf"(?im)^\s*{_section_header_re(header)}(.*?)"
        rf"(?=^\s*{_HEADER_DECORATION}(?:{next_headers}):?{_HEADER_CLOSE}\s*:?\s*|\Z)",
        re.DOTALL,
    )
    match = pattern.search(raw)
    return match.group(1).strip() if match else ""


def _is_section_label_only(text: str) -> bool:
    compact = text.strip()
    if not compact:
        return True
    labels = "|".join(re.escape(name) for name in _SECTION_HEADERS)
    return bool(
        re.fullmatch(
            rf"(?i){_HEADER_DECORATION}(?:{labels}):?{_HEADER_CLOSE}\s*:?\s*",
            compact,
        )
    )


def _bullet_lines(body: str) -> list[str]:
    lines: list[str] = []
    for line in body.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+\.)\s*", "", line).strip()
        if cleaned and not _is_section_label_only(cleaned):
            lines.append(cleaned)
    if lines:
        return lines
    compact = body.strip()
    if compact and not _is_section_label_only(compact):
        return [compact]
    return []


def parse_summary(raw: str, *, title: str = "", message_id: str = "") -> StructuredSummary:
    """Normalize raw LLM output into a StructuredSummary."""
    summary_body = _section_body(raw, "Summary")
    summary_lines = _bullet_lines(summary_body)
    summary = " ".join(summary_lines) if summary_lines else summary_body
    key_points = _bullet_lines(_section_body(raw, "Key points"))
    important_facts = _bullet_lines(_section_body(raw, "Important facts"))
    why_body = _section_body(raw, "Why it matters")
    why_lines = _bullet_lines(why_body)
    why_it_matters = " ".join(why_lines) if why_lines else why_body
    follow_ups = _bullet_lines(_section_body(raw, "Follow-up questions you can ask me"))
    if not follow_ups:
        follow_ups = _bullet_lines(_section_body(raw, "Follow-up questions"))

    if not summary or _is_section_label_only(summary):
        # Fallback: first real paragraph that is not a section label
        summary = ""
        for block in re.split(r"\n\s*\n", raw.strip()):
            candidate = block.strip()
            if candidate and not _is_section_label_only(candidate):
                # Drop a leading label line if the model glued header + body
                lines = candidate.splitlines()
                if lines and _is_section_label_only(lines[0]) and len(lines) > 1:
                    candidate = "\n".join(lines[1:]).strip()
                if candidate and not _is_section_label_only(candidate):
                    summary = candidate
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

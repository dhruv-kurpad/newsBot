"""Local LLM client and newsletter summarizer."""

from newsbot.llm.client import LLMClient
from newsbot.llm.summarizer import StructuredSummary, parse_summary, summarize_article

__all__ = [
    "LLMClient",
    "StructuredSummary",
    "parse_summary",
    "summarize_article",
]

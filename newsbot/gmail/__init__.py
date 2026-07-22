"""Gmail ingestion: auth, fetch, extract, processed-id tracking."""

from newsbot.gmail.client import get_gmail_service, list_new_messages
from newsbot.gmail.extract import extract_article
from newsbot.gmail.processed import ProcessedMessageStore

__all__ = [
    "get_gmail_service",
    "list_new_messages",
    "extract_article",
    "ProcessedMessageStore",
]

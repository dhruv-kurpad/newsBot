"""Persist summaries + embeddings; retrieve for follow-up Q&A."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from newsbot.config import get_settings
from newsbot.llm.summarizer import StructuredSummary

logger = logging.getLogger(__name__)

COLLECTION_NAME = "newsletter_summaries"
LOCAL_EMBED_DIM = 384


@dataclass
class StoredSummary:
    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None


def _local_embedding(text: str, dim: int = LOCAL_EMBED_DIM) -> list[float]:
    """Deterministic bag-of-hashes embedding used when Ollama is unavailable."""
    vector = [0.0] * dim
    tokens = text.lower().split() or [text]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for i in range(0, min(len(digest), 32), 4):
            idx = int.from_bytes(digest[i : i + 4], "little") % dim
            sign = 1.0 if digest[i] % 2 == 0 else -1.0
            vector[idx] += sign
    norm = sum(v * v for v in vector) ** 0.5 or 1.0
    return [v / norm for v in vector]


def embed_text(text: str, *, model: str, base_url: str) -> list[float]:
    """Embed text using a local Ollama embedding model (with offline fallback)."""
    url = f"{base_url.rstrip('/')}/api/embeddings"
    try:
        response = httpx.post(
            url,
            json={"model": model, "prompt": text},
            timeout=60.0,
        )
        response.raise_for_status()
        payload = response.json()
        embedding = payload.get("embedding")
        if isinstance(embedding, list) and embedding:
            return [float(x) for x in embedding]
        raise ValueError("Ollama response missing embedding")
    except Exception as exc:  # noqa: BLE001 — fall back for local/dev without Ollama
        logger.warning("embed_text falling back to local embedding: %s", exc)
        return _local_embedding(text)


def _summary_document(summary: StructuredSummary) -> str:
    parts = [
        f"Title: {summary.title}",
        f"Summary: {summary.summary}",
    ]
    if summary.key_points:
        parts.append("Key points: " + "; ".join(summary.key_points))
    if summary.important_facts:
        parts.append("Important facts: " + "; ".join(summary.important_facts))
    if summary.why_it_matters:
        parts.append(f"Why it matters: {summary.why_it_matters}")
    if summary.follow_up_questions:
        parts.append("Follow-ups: " + "; ".join(summary.follow_up_questions))
    if summary.links:
        parts.append("Links: " + " ".join(summary.links))
    return "\n".join(parts)


def _summary_metadata(summary: StructuredSummary) -> dict[str, Any]:
    return {
        "title": summary.title,
        "message_id": summary.message_id,
        "why_it_matters": summary.why_it_matters,
        "links": json.dumps(summary.links),
        "key_points": json.dumps(summary.key_points),
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }


def _parse_stored_at(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


class VectorStore:
    """Disk-backed Chroma vector store for newsletter summaries."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        import chromadb

        client = chromadb.PersistentClient(path=str(self.path))
        self._collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def store_summary(self, summary: StructuredSummary) -> str:
        """Store summary text + metadata + embedding; return document id."""
        settings = get_settings()
        document = _summary_document(summary)
        embedding = embed_text(
            document,
            model=settings.embedding_model,
            base_url=settings.llm_base_url,
        )
        doc_id = summary.message_id or str(uuid.uuid4())
        collection = self._get_collection()
        collection.upsert(
            ids=[doc_id],
            documents=[document],
            embeddings=[embedding],
            metadatas=[_summary_metadata(summary)],
        )
        return doc_id

    def purge_older_than(self, days: int) -> int:
        """Delete summaries whose ``stored_at`` is older than ``days``. Returns count removed."""
        if days < 0:
            raise ValueError("days must be >= 0")

        collection = self._get_collection()
        if collection.count() == 0:
            return 0

        raw = collection.get(include=["metadatas"])
        ids = raw.get("ids") or []
        metadatas = raw.get("metadatas") or []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        to_delete: list[str] = []
        for doc_id, meta in zip(ids, metadatas):
            stored_at = _parse_stored_at((meta or {}).get("stored_at"))
            if stored_at is None:
                # Legacy docs without a timestamp are left alone
                continue
            if stored_at < cutoff:
                to_delete.append(str(doc_id))

        if to_delete:
            collection.delete(ids=to_delete)
            logger.info("Purged %s summaries older than %s days", len(to_delete), days)
        return len(to_delete)

    def search(self, query: str, *, top_k: int = 5) -> list[StoredSummary]:
        """Retrieve top-k summaries relevant to ``query``."""
        settings = get_settings()
        collection = self._get_collection()
        if collection.count() == 0:
            return []

        embedding = embed_text(
            query,
            model=settings.embedding_model,
            base_url=settings.llm_base_url,
        )
        n_results = min(top_k, collection.count())
        raw = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        ids = (raw.get("ids") or [[]])[0]
        documents = (raw.get("documents") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        results: list[StoredSummary] = []
        for idx, doc_id in enumerate(ids):
            distance = distances[idx] if idx < len(distances) else None
            score = None if distance is None else 1.0 / (1.0 + float(distance))
            results.append(
                StoredSummary(
                    id=str(doc_id),
                    text=documents[idx] if idx < len(documents) else "",
                    metadata=dict(metadatas[idx] or {}) if idx < len(metadatas) else {},
                    score=score,
                )
            )
        return results

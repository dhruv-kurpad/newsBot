"""Track processed Gmail message IDs to avoid duplicate digests."""

from __future__ import annotations

import json
from pathlib import Path


class ProcessedMessageStore:
    """Persist processed message IDs on disk as a JSON list."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._ids: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            self._ids = set()
            return
        # utf-8-sig strips a BOM that Windows editors / PowerShell sometimes add
        raw = self.path.read_text(encoding="utf-8-sig").strip()
        if not raw:
            self._ids = set()
            return
        data = json.loads(raw)
        if isinstance(data, list):
            self._ids = {str(item) for item in data}
        elif isinstance(data, dict) and "ids" in data:
            self._ids = {str(item) for item in data["ids"]}
        else:
            self._ids = set()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = sorted(self._ids)
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def is_processed(self, message_id: str) -> bool:
        return message_id in self._ids

    def mark_processed(self, message_id: str) -> None:
        self._ids.add(message_id)
        self._save()

    def all_ids(self) -> set[str]:
        return set(self._ids)

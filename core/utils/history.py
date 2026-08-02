"""Local, document-content-free operation history."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.config import local_data_dir


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    id: str
    date: str
    filename: str
    action: str
    original_size: int
    output_size: int
    output_path: str
    status: str = "Completed"


class HistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or local_data_dir() / "history.json"

    def load(self) -> list[HistoryEntry]:
        if not self.path.exists(): return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [HistoryEntry(**item) for item in data if isinstance(item, dict)]
        except (OSError, ValueError, TypeError): return []

    def add(self, filename: str, action: str, original_size: int, output_size: int, output_path: str, status: str = "Completed") -> HistoryEntry:
        entry = HistoryEntry(str(uuid4()), datetime.now().isoformat(timespec="seconds"), Path(filename).name, action, original_size, output_size, str(Path(output_path).resolve()), status)
        entries = [entry, *self.load()][:1000]; self._save(entries); return entry

    def delete(self, entry_id: str) -> None: self._save([entry for entry in self.load() if entry.id != entry_id])
    def clear(self) -> None: self._save([])

    def stats(self) -> tuple[int, int]:
        entries = [entry for entry in self.load() if entry.status == "Completed"]
        return len(entries), sum(max(0, entry.original_size - entry.output_size) for entry in entries)

    def _save(self, entries: list[HistoryEntry]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True); temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps([asdict(entry) for entry in entries], indent=2), encoding="utf-8"); temporary.replace(self.path)

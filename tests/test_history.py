from pathlib import Path

from core.utils.history import HistoryStore


def test_history_add_stats_delete_and_clear(tmp_path: Path) -> None:
    store = HistoryStore(tmp_path / "history.json")
    first = store.add("document.pdf", "Compress PDF", 1000, 400, str(tmp_path / "output.pdf"))
    store.add("other.pdf", "Merge PDF", 500, 700, str(tmp_path / "merged.pdf"))
    assert store.stats() == (2, 600)
    store.delete(first.id); assert len(store.load()) == 1
    store.clear(); assert store.load() == []

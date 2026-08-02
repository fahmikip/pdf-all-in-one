from pathlib import Path

from app.config import ConfigStore, Settings


def test_config_round_trip(tmp_path: Path) -> None:
    store = ConfigStore(tmp_path / "settings.json")
    expected = Settings(theme="dark", default_dpi=300)
    store.save(expected)
    assert store.load() == expected


def test_invalid_config_uses_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")
    assert ConfigStore(path).load() == Settings()

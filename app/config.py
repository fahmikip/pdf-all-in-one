"""Application identity and persistent settings."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = (PROJECT_ROOT / "version.txt").read_text(encoding="utf-8").strip()
APP_NAME = "PDF Master"
APP_SLUG = "PDFMaster"
DEVELOPER = "Fahmikip"
GITHUB_URL = "https://github.com/fahmikip"


def local_data_dir() -> Path:
    root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    path = root / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(slots=True)
class Settings:
    theme: str = "system"
    default_output_folder: str = ""
    ask_output_location: bool = True
    remember_last_directory: bool = True
    show_welcome: bool = True
    language: str = "id"
    default_compression: str = "recommended"
    default_dpi: int = 150


class ConfigStore:
    """JSON settings store with safe defaults and atomic writes."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or local_data_dir() / "settings.json"

    def load(self) -> Settings:
        if not self.path.exists():
            return Settings()
        try:
            data: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
            allowed = Settings.__dataclass_fields__.keys()
            return Settings(**{key: value for key, value in data.items() if key in allowed})
        except (OSError, ValueError, TypeError):
            return Settings()

    def save(self, settings: Settings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
        temporary.replace(self.path)

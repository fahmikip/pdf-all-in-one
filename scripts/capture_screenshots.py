"""Render a few app pages offscreen and save screenshots to docs/screenshots/.

Screenshots are generated headlessly (QT_QPA_PLATFORM=offscreen) so they can be
regenerated on any machine or in CI without a display.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)) if str(ROOT) not in sys.path else None

from app.config import ConfigStore, Settings  # noqa: E402
from core.utils.logger import configure_logging  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402

OUT_DIR = ROOT / "docs" / "screenshots"

PAGES = {
    "home": "Beranda",
    "compress": "Kompres PDF",
    "settings": "Pengaturan",
}


def main() -> None:
    configure_logging()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    settings = Settings(check_updates=False)
    window = MainWindow(settings, ConfigStore())
    window.resize(1280, 800)
    window.show()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key in PAGES:
        window.navigate(key)
        app.processEvents()
        app.processEvents()
        path = OUT_DIR / f"{key}.png"
        window.grab().save(str(path))
        print(f"Saved {path}")
    window.close()


if __name__ == "__main__":
    main()

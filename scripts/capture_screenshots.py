"""Render a few app pages offscreen and save screenshots to docs/screenshots/.

Screenshots are generated headlessly (QT_QPA_PLATFORM=offscreen) so they can be
regenerated on any machine or in CI without a display.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)) if str(ROOT) not in sys.path else None

from app.config import ConfigStore, Settings  # noqa: E402
from core.utils.logger import configure_logging  # noqa: E402
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402

OUT_DIR = ROOT / "docs" / "screenshots"

PAGES = {
    "home": "Beranda",
    "compress": "Kompres PDF",
    "layout": "Print Layout",
    "pages": "Page Tools",
    "repair": "Repair & Optimize",
    "settings": "Pengaturan",
}

# Characters the UI relies on that collapse to "tofu" boxes when the fallback
# font that the offscreen platform ships with cannot render them.
REQUIRED_CODEPOINTS = {0x2192, 0x21B6, 0x21B7, 0x2014, 0x2026}


def _font_directories() -> list[Path]:
    if sys.platform == "win32":
        windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
        return [windows / "Fonts"]
    if sys.platform == "darwin":
        return [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path("~/Library/Fonts").expanduser()]
    return [Path("/usr/share/fonts"), Path("~/.fonts").expanduser()]


def _register_system_fonts() -> None:
    """Make real system fonts visible to the offscreen renderer.

    With QT_QPA_PLATFORM=offscreen the font database starts empty, so Qt falls
    back to a built-in font that lacks most glyphs and text renders as boxes.
    Registering the OS fonts fixes the rendering without needing a display.
    """
    registered = 0
    for directory in _font_directories():
        if not directory.is_dir():
            continue
        for pattern in ("*.ttf", "*.ttc", "*.otf"):
            for font_path in directory.glob(pattern):
                if QFontDatabase.addApplicationFont(str(font_path)) >= 0:
                    registered += 1
    family = "Segoe UI" if sys.platform == "win32" else QFont().family()
    app = QApplication.instance()
    if app is not None:
        app.setFont(QFont(family, 10))
    metrics = QFontMetrics(QFont(family, 10))
    missing = sorted(f"U+{codepoint:04X}" for codepoint in REQUIRED_CODEPOINTS if not metrics.inFontUcs4(codepoint))
    print(f"Registered {registered} system font file(s); app font: {family}")
    if missing:
        print(f"Warning: selected font lacks glyphs for {', '.join(missing)}")


def main() -> None:
    configure_logging()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    _register_system_fonts()
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
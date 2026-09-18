"""Permanent developer identity footer."""

from __future__ import annotations

from app.config import DEVELOPER, GITHUB_URL, VERSION
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QStatusBar

from ui.themes.palette import rgba


class Footer(QStatusBar):
    def __init__(self, dark: bool = False) -> None:
        super().__init__()
        self._dark = dark
        self._colors = {}
        self.identity = QLabel()
        self.identity.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.identity.setOpenExternalLinks(False)
        self.identity.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        self.addPermanentWidget(self.identity)
        self.set_dark(dark)

    def set_dark(self, dark: bool) -> None:
        self._dark = dark
        if dark:
            self._colors = {
                "bar_bg": rgba("#1E293B", 0.45),
                "bar_border": rgba("#94A3B8", 0.25),
                "text": "#94A3B8",
                "sep": "#475569",
                "link": "#A5B4FC",
            }
        else:
            self._colors = {
                "bar_bg": rgba("#FFFFFF", 0.55),
                "bar_border": rgba("#64748B", 0.22),
                "text": "#64748B",
                "sep": "#CBD5E1",
                "link": "#4F46E5",
            }
        self.setStyleSheet(
            f"QStatusBar {{ background: {self._colors['bar_bg']}; "
            f"border-top: 1px solid {self._colors['bar_border']}; "
            f"color: {self._colors['text']}; padding: 2px 10px; }}"
        )
        self.showMessage("Siap")
        self.identity.setText(
            f'<span style="color:{self._colors["text"]};">PDF Master v{VERSION}</span>  '
            f'<span style="color:{self._colors["sep"]};">|</span>  '
            f'<span style="color:{self._colors["text"]};">Dikembangkan oleh '
            f'<b style="color:{self._colors["link"]};">{DEVELOPER}</b></span>  '
            f'<span style="color:{self._colors["sep"]};">|</span>  '
            f'<a style="color:{self._colors["link"]}; text-decoration:none;" href="{GITHUB_URL}">GitHub</a>  '
            f'<span style="color:{self._colors["sep"]};">|</span>  '
            f'<span style="color:{self._colors["text"]};">\u00a9 2026 {DEVELOPER}</span>'
        )
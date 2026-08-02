"""Permanent developer identity footer."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QStatusBar

from app.config import DEVELOPER, GITHUB_URL, VERSION


class Footer(QStatusBar):
    def __init__(self) -> None:
        super().__init__()
        self.showMessage("Ready")
        identity = QLabel(
            f'PDF Master v{VERSION}  •  Developed by {DEVELOPER}  •  '
            f'<a style="color:#6366F1" href="{GITHUB_URL}">GitHub</a>  •  © 2026 {DEVELOPER}'
        )
        identity.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        identity.setOpenExternalLinks(False)
        identity.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        self.addPermanentWidget(identity)

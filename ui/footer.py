"""Permanent developer identity footer."""

from __future__ import annotations

from app.config import DEVELOPER, GITHUB_URL, VERSION
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QStatusBar


class Footer(QStatusBar):
    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(
            "QStatusBar { background: #111827; border-top: 1px solid #263449; color: #94A3B8; padding: 2px 8px; }"
        )
        self.showMessage("Ready")
        identity = QLabel(
            f'<span style="color:#94A3B8;">PDF Master v{VERSION}</span>  '
            f'<span style="color:#475569;">|</span>  '
            f'<span style="color:#94A3B8;">Developed by <b style="color:#818CF8;">{DEVELOPER}</b></span>  '
            f'<span style="color:#475569;">|</span>  '
            f'<a style="color:#38BDF8; text-decoration:none;" href="{GITHUB_URL}">GitHub</a>  '
            f'<span style="color:#475569;">|</span>  '
            f'<span style="color:#94A3B8;">\u00a9 2026 {DEVELOPER}</span>'
        )
        identity.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        identity.setOpenExternalLinks(False)
        identity.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        self.addPermanentWidget(identity)

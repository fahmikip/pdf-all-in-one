"""Developer profile and application identity."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from app.config import DEVELOPER, GITHUB_URL, PROJECT_ROOT, VERSION


def avatar_pixmap(size: int = 128) -> QPixmap:
    source = PROJECT_ROOT / "assets" / "developer" / "developer.jpg"
    pixmap = QPixmap(str(source))
    if pixmap.isNull():
        pixmap = QPixmap(size, size)
        pixmap.fill("#6366F1")
        painter = QPainter(pixmap)
        painter.setPen(Qt.GlobalColor.white)
        font = painter.font(); font.setPointSize(38); font.setBold(True); painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "F")
        painter.end()
    pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
    result = QPixmap(size, size); result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath(); path.addEllipse(0, 0, size, size); painter.setClipPath(path); painter.drawPixmap(0, 0, pixmap); painter.end()
    return result


class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 42, 60, 42)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        heading = QLabel("About Developer"); heading.setObjectName("title"); layout.addWidget(heading, alignment=Qt.AlignmentFlag.AlignHCenter)
        card = QFrame(); card.setObjectName("card"); card.setMaximumWidth(620)
        card_layout = QVBoxLayout(card); card_layout.setContentsMargins(42, 36, 42, 36); card_layout.setSpacing(10)
        avatar = QLabel(); avatar.setPixmap(avatar_pixmap()); card_layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignHCenter)
        name = QLabel(DEVELOPER); name.setObjectName("title"); card_layout.addWidget(name, alignment=Qt.AlignmentFlag.AlignHCenter)
        role = QLabel("Developer of PDF Master"); role.setObjectName("subtitle"); card_layout.addWidget(role, alignment=Qt.AlignmentFlag.AlignHCenter)
        info = QLabel(f"PDF Master · Version {VERSION} · Windows\nBuilt with Python & PySide6\n© 2026 {DEVELOPER}")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter); info.setObjectName("muted"); card_layout.addWidget(info)
        button = QPushButton("Visit GitHub"); button.setObjectName("primary"); button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL))); card_layout.addWidget(button)
        privacy = QLabel("Privacy: files are processed locally. No telemetry, analytics, or document uploads.")
        privacy.setWordWrap(True); privacy.setAlignment(Qt.AlignmentFlag.AlignCenter); privacy.setObjectName("muted"); card_layout.addWidget(privacy)
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)

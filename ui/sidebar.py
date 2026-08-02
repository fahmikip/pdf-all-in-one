"""Primary application navigation."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout


class Sidebar(QFrame):
    page_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(230)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 22, 18, 18)
        layout.setSpacing(5)
        brand = QLabel("◆  PDF Master")
        brand.setObjectName("brand")
        layout.addWidget(brand)
        caption = QLabel("Offline PDF Toolkit")
        caption.setObjectName("muted")
        layout.addWidget(caption)
        layout.addSpacing(24)
        self.buttons: dict[str, QPushButton] = {}
        groups = {
            "": [("home", "⌂  Home")],
            "PDF TOOLS": [("compress", "▣  Compress PDF"), ("merge", "⊕  Merge PDF"), ("split", "✂  Split PDF"), ("organize", "▦  Organize PDF")],
            "CONVERT": [("convert", "⇄  Convert Files")],
            "EDIT": [("edit", "✎  Watermark & More")],
            "SECURITY": [("security", "◆  Protect / Unlock")],
            "MORE": [("history", "◷  History"), ("settings", "⚙  Settings"), ("about", "●  About Developer")],
        }
        for heading, entries in groups.items():
            if heading:
                layout.addSpacing(13)
                label = QLabel(heading)
                label.setObjectName("muted")
                layout.addWidget(label)
            for key, text in entries:
                button = QPushButton(text)
                button.setCheckable(True)
                button.clicked.connect(lambda checked=False, page=key: self.select(page))
                layout.addWidget(button)
                self.buttons[key] = button
        layout.addStretch()
        privacy = QLabel("🔒 Files stay on this computer")
        privacy.setObjectName("muted")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)
        self.select("home")

    def select(self, page: str) -> None:
        for key, button in self.buttons.items():
            button.setChecked(key == page)
        self.page_requested.emit(page)

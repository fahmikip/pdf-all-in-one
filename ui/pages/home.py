"""Home dashboard."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ui.widgets.drop_zone import DropZone
from ui.icons import colored_icon
from core.utils.history import HistoryStore


class HomePage(QScrollArea):
    tool_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        content = QWidget()
        self.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(34, 28, 34, 34)
        layout.setSpacing(18)
        title = QLabel("PDF Master")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("All-in-One Offline PDF Toolkit")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(6)
        quick = QLabel("Quick actions")
        quick.setObjectName("section")
        layout.addWidget(quick)
        grid = QGridLayout()
        grid.setSpacing(12)
        actions = [
            ("compress", "Compress PDF", "Reduce file size safely", "indigo", "#4F46E5"),
            ("merge", "Merge PDF", "Combine files in any order", "emerald", "#059669"),
            ("split", "Split PDF", "Extract pages or ranges", "amber", "#D97706"),
            ("convert", "Convert PDF", "PDF and image conversion", "cyan", "#0891B2"),
            ("organize", "Organize PDF", "Reorder, rotate, remove", "violet", "#7C3AED"),
            ("ocr", "OCR PDF", "Make scans searchable", "rose", "#E11D48"),
        ]
        for index, (key, name, description, accent, color) in enumerate(actions):
            card = QFrame()
            card.setObjectName("quickCard")
            card.setProperty("accent", accent)
            card_layout = QVBoxLayout(card)
            header = QHBoxLayout()
            glyph = QLabel(); glyph.setPixmap(colored_icon(key, color, 21).pixmap(21, 21)); header.addWidget(glyph)
            label = QLabel(name)
            label.setObjectName("section")
            header.addWidget(label, 1); card_layout.addLayout(header)
            detail = QLabel(description)
            detail.setObjectName("muted")
            card_layout.addWidget(detail)
            button = QPushButton("Open tool  →")
            button.clicked.connect(lambda checked=False, tool=key: self.tool_requested.emit(tool))
            card_layout.addWidget(button)
            grid.addWidget(card, index // 3, index % 3)
        layout.addLayout(grid)
        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)
        stats = QGridLayout()
        self.stat_values = []
        for index, (value, label, accent) in enumerate((("0", "Total PDF Processed", "indigo"), ("0 MB", "Storage Saved", "emerald"), ("—", "Recent Files", "cyan"))):
            card = QFrame()
            card.setObjectName("statCard")
            card.setProperty("accent", accent)
            card_layout = QVBoxLayout(card)
            number = QLabel(value)
            number.setObjectName("section")
            self.stat_values.append(number)
            card_layout.addWidget(number)
            caption = QLabel(label)
            caption.setObjectName("muted")
            card_layout.addWidget(caption)
            stats.addWidget(card, 0, index)
        layout.addLayout(stats)
        self.refresh_stats()

    def showEvent(self, event) -> None:
        self.refresh_stats(); super().showEvent(event)

    def refresh_stats(self) -> None:
        count, saved = HistoryStore().stats(); entries = HistoryStore().load()
        self.stat_values[0].setText(str(count)); self.stat_values[1].setText(f"{saved / 1048576:.2f} MB"); self.stat_values[2].setText(entries[0].filename if entries else "—")

"""Home dashboard."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ui.widgets.drop_zone import DropZone


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
        actions = [("compress", "Compress PDF", "Reduce file size safely"), ("merge", "Merge PDF", "Combine files in any order"), ("split", "Split PDF", "Extract pages or ranges"), ("convert", "Convert PDF", "PDF and image conversion"), ("organize", "Organize PDF", "Reorder, rotate, remove"), ("ocr", "OCR PDF", "Make scans searchable")]
        for index, (key, name, description) in enumerate(actions):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            label = QLabel(name)
            label.setObjectName("section")
            card_layout.addWidget(label)
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
        for index, (value, label) in enumerate((("0", "Total PDF Processed"), ("0 MB", "Storage Saved"), ("—", "Recent Files"))):
            card = QFrame()
            card.setObjectName("card")
            card_layout = QVBoxLayout(card)
            number = QLabel(value)
            number.setObjectName("section")
            card_layout.addWidget(number)
            caption = QLabel(label)
            caption.setObjectName("muted")
            card_layout.addWidget(caption)
            stats.addWidget(card, 0, index)
        layout.addLayout(stats)

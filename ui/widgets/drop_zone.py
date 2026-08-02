"""Accessible drag-and-drop file target."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout
from ui.icons import icon as app_icon


class DropZone(QFrame):
    files_dropped = Signal(list)
    choose_requested = Signal()

    def __init__(self, title: str = "Drag & Drop PDF Here", multiple: bool = False) -> None:
        super().__init__()
        self.multiple = multiple
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(185)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(8)
        icon_label = QLabel()
        icon_label.setPixmap(app_icon("download", 30).pixmap(30, 30))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(icon_label)
        title_label = QLabel(title)
        title_label.setObjectName("section")
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title_label)
        hint = QLabel("Your documents are processed locally and never uploaded.")
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(hint)
        choose = QPushButton("Choose File")
        choose.setObjectName("primary")
        choose.setMaximumWidth(140)
        choose.clicked.connect(self.choose_requested)
        layout.addWidget(choose, alignment=Qt.AlignmentFlag.AlignHCenter)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any(Path(url.toLocalFile()).suffix.lower() == ".pdf" for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        files = [url.toLocalFile() for url in event.mimeData().urls() if Path(url.toLocalFile()).suffix.lower() == ".pdf"]
        if files:
            self.files_dropped.emit(files if self.multiple else files[:1])
            event.acceptProposedAction()

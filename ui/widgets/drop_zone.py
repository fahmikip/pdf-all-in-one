"""Accessible drag-and-drop file target with colorful design."""

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
        self.setStyleSheet("QFrame#dropZone:hover {  border-color: #4F46E5; border-width: 2.5px;}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(8)
        icon_label = QLabel()
        icon_label.setPixmap(app_icon("download", 30).pixmap(30, 30))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(icon_label)
        title_label = QLabel(title)
        title_label.setObjectName("section")
        title_label.setStyleSheet("color: #4F46E5; font-weight: 650; font-size: 17px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title_label)
        hint = QLabel("Your documents are processed locally and never uploaded.")
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(hint)
        choose = QPushButton("Choose File")
        choose.setStyleSheet(
            "QPushButton {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #818CF8, stop:1 #4F46E5);"
            "  color: white; font-weight: 600; padding: 10px 22px;"
            "  border-radius: 9px; border: none; max-width: 150px;"
            "}"
            "QPushButton:hover {"
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,"
            "    stop:0 #6366F1, stop:1 #4338CA);"
            "}"
            "QPushButton:pressed { background: #4338CA; }"
        )
        choose.setMaximumWidth(150)
        choose.clicked.connect(self.choose_requested)
        layout.addWidget(choose, alignment=Qt.AlignmentFlag.AlignHCenter)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and any(
            Path(url.toLocalFile()).suffix.lower() == ".pdf" for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        files = [
            url.toLocalFile() for url in event.mimeData().urls() if Path(url.toLocalFile()).suffix.lower() == ".pdf"
        ]
        if files:
            self.files_dropped.emit(files if self.multiple else files[:1])
            event.acceptProposedAction()

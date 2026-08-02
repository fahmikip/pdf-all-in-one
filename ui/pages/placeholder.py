"""Informative page used while tools are introduced milestone by milestone."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PlaceholderPage(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self); layout.setContentsMargins(40, 40, 40, 40); layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        heading = QLabel(title); heading.setObjectName("title"); layout.addWidget(heading)
        detail = QLabel("This workspace is ready for its processing engine in the next milestone.")
        detail.setObjectName("subtitle"); layout.addWidget(detail)

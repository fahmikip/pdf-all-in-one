"""Primary application navigation with color-coded sections."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ui.icons import icon

SECTION_COLORS = {
    "ALAT PDF": "#6366F1",
    "ALAT HALAMAN": "#10B981",
    "KONVERSI": "#14B8A6",
    "EDIT": "#F59E0B",
    "KEAMANAN": "#F43F5E",
    "OCR": "#8B5CF6",
    "LANJUTAN": "#06B6D4",
    "LAINNYA": "#94A3B8",
}


class Sidebar(QFrame):
    page_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("sidebar")
        self.setFixedWidth(238)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 12)
        layout.setSpacing(4)
        brand_row = QHBoxLayout()
        brand_row.setContentsMargins(6, 0, 6, 0)
        brand_row.setSpacing(9)
        brand_icon = QLabel()
        brand_icon.setPixmap(icon("app", 22).pixmap(22, 22))
        brand_row.addWidget(brand_icon)
        brand = QLabel("PDF Master")
        brand.setObjectName("brand")
        brand_row.addWidget(brand, 1)
        layout.addLayout(brand_row)
        caption = QLabel("Perangkat PDF Offline")
        caption.setObjectName("muted")
        caption.setContentsMargins(6, 0, 6, 0)
        layout.addWidget(caption)
        layout.addSpacing(10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("sidebarScroll")
        navigation = QWidget()
        navigation.setObjectName("sidebarNavigation")
        navigation_layout = QVBoxLayout(navigation)
        navigation_layout.setContentsMargins(0, 0, 4, 0)
        navigation_layout.setSpacing(2)
        self.buttons: dict[str, QPushButton] = {}
        groups = {
            "": [("home", "Beranda")],
            "ALAT PDF": [
                ("compress", "Kompres PDF"),
                ("merge", "Gabung PDF"),
                ("split", "Pecah PDF"),
                ("organize", "Susun PDF"),
                ("extract", "Ekstrak PDF"),
                ("layout", "Print Layout"),
            ],
            "ALAT HALAMAN": [("pages", "Alat Halaman")],
            "KONVERSI": [("convert", "Konversi File")],
            "EDIT": [("edit", "Watermark & Lainnya"), ("forms", "Form PDF & Tanda Tangan")],
            "KEAMANAN": [("security", "Amankan / Buka Kunci")],
            "OCR": [("ocr", "OCR PDF / Gambar")],
            "LANJUTAN": [("batch", "Proses Batch"), ("repair", "Perbaiki & Optimalkan")],
            "LAINNYA": [("history", "Riwayat"), ("settings", "Pengaturan"), ("about", "Tentang Developer")],
        }
        for heading, entries in groups.items():
            if heading:
                navigation_layout.addSpacing(7)
                label = QLabel(heading)
                label.setStyleSheet(
                    f"color: {SECTION_COLORS[heading]}; font-weight: 700; font-size: 11px; letter-spacing: 1px;"
                )
                label.setContentsMargins(8, 0, 0, 0)
                navigation_layout.addWidget(label)
            for key, text in entries:
                button = QPushButton(text)
                button.setIcon(icon(key))
                button.setIconSize(QSize(18, 18))
                button.setCheckable(True)
                button.clicked.connect(lambda checked=False, page=key: self.select(page))
                button.setMinimumHeight(34)
                navigation_layout.addWidget(button)
                self.buttons[key] = button
        navigation_layout.addStretch()
        scroll.setWidget(navigation)
        layout.addWidget(scroll, 1)
        privacy = QLabel("File tetap berada di komputer ini")
        privacy.setObjectName("muted")
        privacy.setWordWrap(True)
        privacy.setContentsMargins(6, 5, 6, 0)
        layout.addWidget(privacy)
        self.select("home")

    def select(self, page: str) -> None:
        for key, button in self.buttons.items():
            button.setChecked(key == page)
        self.page_requested.emit(page)

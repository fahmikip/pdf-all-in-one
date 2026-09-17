"""Local processing history page."""

from pathlib import Path

from core.utils.history import HistoryStore
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class HistoryPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.store = HistoryStore()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 28)
        title = QLabel("Riwayat")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Hanya detail operasi yang disimpan secara lokal—bukan isi dokumen.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Tanggal", "Nama File", "Aksi", "Ukuran Asli", "Output", "Status"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        refresh = QPushButton("Muat Ulang")
        refresh.setObjectName("ghost")
        refresh.clicked.connect(self.refresh)
        open_file = QPushButton("Buka File")
        open_file.setObjectName("ghost")
        open_file.clicked.connect(self.open_file)
        open_folder = QPushButton("Buka Folder")
        open_folder.setObjectName("ghost")
        open_folder.clicked.connect(self.open_folder)
        delete = QPushButton("Hapus Entri")
        delete.setObjectName("danger")
        delete.clicked.connect(self.delete)
        clear = QPushButton("Bersihkan Riwayat")
        clear.setObjectName("danger")
        clear.clicked.connect(self.clear)
        for button in (refresh, open_file, open_folder, delete, clear):
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        self.refresh()

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)

    def refresh(self) -> None:
        entries = self.store.load()
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = (
                entry.date.replace("T", " "),
                entry.filename,
                entry.action,
                self._size(entry.original_size),
                self._size(entry.output_size),
                entry.status,
            )
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            self.table.item(row, 0).setData(256, (entry.id, entry.output_path))
        self.table.resizeColumnsToContents()

    def _selected(self):
        row = self.table.currentRow()
        return self.table.item(row, 0).data(256) if row >= 0 and self.table.item(row, 0) else None

    def open_file(self) -> None:
        selected = self._selected()
        if selected and Path(selected[1]).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(selected[1]))

    def open_folder(self) -> None:
        selected = self._selected()
        if selected:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(selected[1]).parent)))

    def delete(self) -> None:
        selected = self._selected()
        if selected:
            self.store.delete(selected[0])
            self.refresh()

    def clear(self) -> None:
        if (
            QMessageBox.question(self, "Bersihkan riwayat", "Hapus semua entri riwayat lokal?")
            == QMessageBox.StandardButton.Yes
        ):
            self.store.clear()
            self.refresh()

    @staticmethod
    def _size(value: int) -> str:
        return f"{value / 1048576:.2f} MB" if value >= 1048576 else f"{value / 1024:.1f} KB"

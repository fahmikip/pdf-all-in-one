"""Tabbed PDF editing tools."""

from __future__ import annotations

from pathlib import Path

from core.jobs.worker import FunctionWorker
from core.pdf.metadata import read_metadata, write_metadata
from core.pdf.watermark import add_header_footer, add_image_watermark, add_page_numbers, add_text_watermark
from core.utils.validation import validate_pdf
from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.pages.editor import EditorPage


class EditPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.worker = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 28)
        title = QLabel("Edit PDF")
        title.setObjectName("title")
        layout.addWidget(title)
        source_row = QHBoxLayout()
        self.source_label = QLabel("Belum ada PDF dipilih")
        choose = QPushButton("Pilih PDF")
        choose.setObjectName("ghost")
        choose.clicked.connect(self.choose_pdf)
        source_row.addWidget(self.source_label, 1)
        source_row.addWidget(choose)
        layout.addLayout(source_row)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self._watermark_tab()
        self._numbers_tab()
        self._header_tab()
        self._metadata_tab()
        self._editor_tab()
        self.status = QLabel("Semua perubahan disimpan ke file baru.")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)

    def choose_pdf(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Pilih PDF", "", "Berkas PDF (*.pdf)")
        if not name:
            return
        self.load_pdf(name)

    def load_pdf(self, path: str | Path) -> bool:
        """Load a PDF for every editing tab, including Insert & Edit."""
        try:
            self.source = validate_pdf(path).path
        except Exception as exc:
            QMessageBox.warning(self, "Tidak Dapat Membuka PDF", str(exc))
            return False
        self.source_label.setText(self.source.name)
        self._load_metadata()
        self.editor.load_pdf(self.source)
        return True

    def _watermark_tab(self) -> None:
        page = QWidget()
        form = QFormLayout(page)
        self.wm_type = QComboBox()
        self.wm_type.addItems(["Teks", "Gambar"])
        form.addRow("Tipe", self.wm_type)
        self.wm_content = QLineEdit("RAHASIA")
        form.addRow("Teks / jalur gambar", self.wm_content)
        browse = QPushButton("Jelajahi gambar")
        browse.setObjectName("ghost")
        browse.clicked.connect(self.choose_watermark_image)
        form.addRow("", browse)
        self.wm_position = QComboBox()
        self.wm_position.addItems(
            ["center", "top-left", "top-center", "top-right", "bottom-left", "bottom-center", "bottom-right"]
        )
        form.addRow("Posisi", self.wm_position)
        self.wm_opacity = QSpinBox()
        self.wm_opacity.setRange(5, 100)
        self.wm_opacity.setValue(25)
        form.addRow("Opasitas (%)", self.wm_opacity)
        self.wm_rotation = QComboBox()
        self.wm_rotation.addItems(["0", "90", "180", "270"])
        form.addRow("Rotasi", self.wm_rotation)
        self.wm_pages = QLineEdit()
        self.wm_pages.setPlaceholderText("Semua, atau 1-3, 5")
        form.addRow("Halaman", self.wm_pages)
        button = QPushButton("Tambahkan Watermark")
        button.setObjectName("info")
        button.clicked.connect(self.apply_watermark)
        form.addRow(button)
        self.tabs.addTab(page, "Watermark")

    def _numbers_tab(self) -> None:
        page = QWidget()
        form = QFormLayout(page)
        self.number_template = QComboBox()
        self.number_template.setEditable(True)
        self.number_template.addItems(["{page}", "Halaman {page}", "{page} / {pages}"])
        form.addRow("Format", self.number_template)
        self.number_position = QComboBox()
        self.number_position.addItems(
            ["bottom-center", "bottom-left", "bottom-right", "top-center", "top-left", "top-right"]
        )
        form.addRow("Posisi", self.number_position)
        self.number_start = QSpinBox()
        self.number_start.setRange(0, 999999)
        self.number_start.setValue(1)
        form.addRow("Nomor awal", self.number_start)
        self.number_pages = QLineEdit()
        self.number_pages.setPlaceholderText("Semua, atau 1-3, 5")
        form.addRow("Halaman", self.number_pages)
        button = QPushButton("Tambahkan Nomor Halaman")
        button.setObjectName("info")
        button.clicked.connect(self.apply_numbers)
        form.addRow(button)
        self.tabs.addTab(page, "Nomor Halaman")

    def _header_tab(self) -> None:
        page = QWidget()
        form = QFormLayout(page)
        label_map = {
            "header-left": "Header Kiri",
            "header-center": "Header Tengah",
            "header-right": "Header Kanan",
            "footer-left": "Footer Kiri",
            "footer-center": "Footer Tengah",
            "footer-right": "Footer Kanan",
        }
        self.header_fields = {}
        for key in label_map:
            edit = QLineEdit()
            edit.setPlaceholderText("Dukung {page}, {pages}, {date}, {filename}")
            self.header_fields[key] = edit
            form.addRow(label_map[key], edit)
        button = QPushButton("Tambahkan Header & Footer")
        button.setObjectName("info")
        button.clicked.connect(self.apply_header)
        form.addRow(button)
        self.tabs.addTab(page, "Header & Footer")

    def _metadata_tab(self) -> None:
        page = QWidget()
        form = QFormLayout(page)
        self.metadata_fields = {}
        for key in ("title", "author", "subject", "keywords", "creator", "producer"):
            edit = QLineEdit()
            self.metadata_fields[key] = edit
            form.addRow(key.title(), edit)
        row = QHBoxLayout()
        save = QPushButton("Simpan Metadata")
        save.setObjectName("success")
        save.clicked.connect(lambda: self.apply_metadata(False))
        clear = QPushButton("Bersihkan Metadata")
        clear.setObjectName("ghost")
        clear.clicked.connect(lambda: self.apply_metadata(True))
        row.addWidget(save)
        row.addWidget(clear)
        form.addRow(row)
        self.tabs.addTab(page, "Metadata")

    def choose_watermark_image(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Pilih gambar watermark", "", "Gambar (*.png *.jpg *.jpeg *.webp)")
        if name:
            self.wm_type.setCurrentText("Gambar")
            self.wm_content.setText(name)

    def _editor_tab(self) -> None:
        self.editor = EditorPage()
        self.tabs.addTab(self.editor, "Sisip & Edit")

    def _output(self, suffix: str) -> str:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return ""
        name, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan PDF hasil edit",
            str(self.source.with_name(f"{self.source.stem}_{suffix}.pdf")),
            "Berkas PDF (*.pdf)",
        )
        return name

    def _run(self, function, output: str, *args, **kwargs) -> None:
        if not self.source or not output:
            return
        self.status.setText("Memproses…")
        worker = FunctionWorker(function, self.source, output, *args, **kwargs)
        self.worker = worker
        worker.signals.result.connect(lambda result: self._complete(Path(result)))
        worker.signals.error.connect(lambda message, details: QMessageBox.critical(self, "Edit gagal", message))
        worker.signals.finished.connect(lambda: setattr(self, "worker", None))
        QThreadPool.globalInstance().start(worker)

    def _complete(self, output: Path) -> None:
        self.status.setText(f"Tersimpan: {output.name}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

    def apply_watermark(self) -> None:
        output = self._output("watermarked")
        common = {
            "opacity": self.wm_opacity.value() / 100,
            "position": self.wm_position.currentText(),
            "page_range": self.wm_pages.text(),
        }
        if self.wm_type.currentText() == "Image":
            self._run(add_image_watermark, output, self.wm_content.text(), **common)
        else:
            self._run(
                add_text_watermark,
                output,
                self.wm_content.text(),
                rotation=int(self.wm_rotation.currentText()),
                **common,
            )

    def apply_numbers(self) -> None:
        output = self._output("numbered")
        self._run(
            add_page_numbers,
            output,
            template=self.number_template.currentText(),
            position=self.number_position.currentText(),
            start_number=self.number_start.value(),
            page_range=self.number_pages.text(),
        )

    def apply_header(self) -> None:
        output = self._output("header_footer")
        self._run(add_header_footer, output, {key: field.text() for key, field in self.header_fields.items()})

    def _load_metadata(self) -> None:
        if self.source:
            for key, value in read_metadata(self.source).items():
                self.metadata_fields[key].setText(value)

    def apply_metadata(self, clear: bool) -> None:
        output = self._output("metadata")
        self._run(
            write_metadata, output, {key: field.text() for key, field in self.metadata_fields.items()}, clear=clear
        )

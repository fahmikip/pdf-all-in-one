"""Print Layout: arrange several pages per sheet or create a duplex booklet."""

from __future__ import annotations

from pathlib import Path

from core.pdf.impose import impose_pages
from core.utils.history import HistoryStore
from core.utils.validation import validate_pdf
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
)

from ui.pages.pdf_tools import ToolPage
from ui.widgets.drop_zone import DropZone


class PrintLayoutPage(ToolPage):
    def __init__(self) -> None:
        super().__init__(
            "Tata Letak Cetak",
            "Letakkan beberapa halaman dalam satu lembar, atau buat buklet yang terlipat setelah pencetakan dua sisi.",
        )
        self.source: Path | None = None
        self.drop = DropZone()
        self.layout.insertWidget(2, self.drop)
        self.drop.choose_requested.connect(self.choose)
        self.drop.files_dropped.connect(self.set_files)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Halaman per lembar"))
        self.pages_per_sheet = QComboBox()
        self.pages_per_sheet.addItems(["2", "4", "6", "8", "9", "16"])
        controls.addWidget(self.pages_per_sheet)
        controls.addWidget(QLabel("Margin"))
        self.margin = QSpinBox()
        self.margin.setRange(0, 200)
        self.margin.setValue(4)
        self.margin.setSuffix(" pt")
        controls.addWidget(self.margin)
        self.booklet = QCheckBox("Buklet (lipat)")
        self.booklet.setToolTip(
            "Dua halaman per lembar sesuai urutan lipat tengah. Cetak bolak-balik, lipat, dan jilid untuk dibaca seperti buklet."
        )
        controls.addWidget(self.booklet)
        controls.addStretch()
        self.process = QPushButton("Buat Tata Letak")
        self.process.setObjectName("success")
        self.process.clicked.connect(self.start)
        controls.addWidget(self.process)
        self.layout.insertLayout(3, controls)
        self.booklet.toggled.connect(self._booklet_changed)
        self.layout.addStretch()

    def _booklet_changed(self, checked: bool) -> None:
        self.pages_per_sheet.setEnabled(not checked)
        if checked:
            self.pages_per_sheet.setCurrentText("2")

    def choose(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Pilih PDF", "", "Berkas PDF (*.pdf)")
        if filename:
            self.set_files([filename])

    def set_files(self, files: list[str]) -> None:
        try:
            info = validate_pdf(files[0])
        except Exception as exc:
            self._error(str(exc), "")
            return
        self.source = info.path
        self.status.setText(f"Dipilih: {info.path.name} · {info.pages} halaman")

    def start(self) -> None:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        suggested = self.source.with_name(f"{self.source.stem}_layout.pdf")
        output, _ = QFileDialog.getSaveFileName(self, "Simpan tata letak cetak", str(suggested), "Berkas PDF (*.pdf)")
        if not output:
            return
        self.run_job(
            impose_pages,
            self.source,
            output,
            pages_per_sheet=int(self.pages_per_sheet.currentText()),
            booklet=self.booklet.isChecked(),
            margin=float(self.margin.value()),
            with_progress=True,
        )

    def _success(self, result: object) -> None:
        super()._success(result)
        if isinstance(result, Path) and self.source:
            HistoryStore().add(
                self.source.name,
                "Tata Letak Cetak" if not self.booklet.isChecked() else "Buklet",
                self.source.stat().st_size,
                result.stat().st_size,
                str(result),
            )

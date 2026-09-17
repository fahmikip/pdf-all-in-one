"""Operational Compress, Merge, and Split pages."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.jobs.worker import FunctionWorker
from core.pdf.compressor import CompressionResult, compress_pdf, find_ghostscript
from core.pdf.merger import merge_pdfs
from core.pdf.splitter import extract_range, split_every_n
from core.utils.history import HistoryStore
from core.utils.validation import validate_pdf
from PySide6.QtCore import Qt, QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.drop_zone import DropZone


def _format_size(size: int) -> str:
    return f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024 * 1024):.2f} MB"


class ToolPage(QWidget):
    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.pool = QThreadPool.globalInstance()
        self.last_result: Path | None = None
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(38, 30, 38, 30)
        self.layout.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("title")
        self.layout.addWidget(heading)
        subtitle = QLabel(description)
        subtitle.setObjectName("subtitle")
        self.layout.addWidget(subtitle)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        self.layout.addWidget(self.progress)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.layout.addWidget(self.status)
        self.open_button = QPushButton("Buka Hasil")
        self.open_button.setObjectName("success")
        self.open_button.hide()
        self.open_button.clicked.connect(self._open_result)
        self.layout.addWidget(self.open_button)

    def run_job(self, function: Callable[..., Any], *args: Any, with_progress: bool = False, **kwargs: Any) -> None:
        self.progress.setValue(0)
        self.progress.show()
        self.open_button.hide()
        self.status.setText("Memproses…")
        worker = FunctionWorker(function, *args, with_progress=with_progress, **kwargs)
        worker.signals.progress.connect(self._progress)
        worker.signals.result.connect(self._success)
        worker.signals.error.connect(self._error)
        worker.signals.finished.connect(lambda: self.progress.hide())
        self.pool.start(worker)

    def _progress(self, value: int, detail: str) -> None:
        self.progress.setValue(value)
        self.status.setText(detail)

    def _success(self, result: object) -> None:
        if isinstance(result, CompressionResult):
            self.last_result = result.output
            if result.saved_bytes:
                self.status.setText(
                    f"Kompresi selesai · {_format_size(result.original_size)} → "
                    f"{_format_size(result.compressed_size)} · Hemat {result.reduction_percent:.1f}%"
                )
            else:
                self.status.setText("PDF sudah optimal · Salinan keluaran yang aman dibuat")
        elif isinstance(result, list):
            self.last_result = Path(result[0]).parent if result else None
            self.status.setText(f"Pecah selesai · {len(result)} file dibuat")
        else:
            self.last_result = Path(result) if result else None
            self.status.setText("Operasi selesai dengan sukses")
        self.progress.setValue(100)
        self.open_button.setText("Buka Folder" if self.last_result and self.last_result.is_dir() else "Buka Hasil")
        self.open_button.setVisible(self.last_result is not None)

    def _error(self, message: str, details: str) -> None:
        self.status.setText("Operasi gagal")
        dialog = QMessageBox(QMessageBox.Icon.Critical, "Terjadi kesalahan", message, parent=self)
        dialog.setInformativeText("File asli Anda tidak diubah.")
        dialog.setDetailedText(details)
        dialog.exec()

    def _open_result(self) -> None:
        if self.last_result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_result)))


class CompressPage(ToolPage):
    def __init__(self, default_level: str = "recommended") -> None:
        super().__init__("Kompres PDF", "Kecilkan ukuran file PDF secara lokal tanpa mengubah file asli.")
        self.source: Path | None = None
        self.drop = DropZone()
        self.layout.insertWidget(2, self.drop)
        self.drop.choose_requested.connect(self.choose)
        self.drop.files_dropped.connect(self.set_files)
        row = QHBoxLayout()
        row.addWidget(QLabel("Mesin"))
        self.engine = QComboBox()
        self.engine.addItem("Bawaan", "builtin")
        self.engine.addItem("Lossless (qpdf)", "qpdf")
        if find_ghostscript():
            self.engine.addItem("Ghostscript (terbaik untuk scan)", "ghostscript")
        else:
            self.engine.addItem("Ghostscript (pasang untuk mengaktifkan)", "ghostscript")
            self.engine.setItemData(self.engine.count() - 1, 0, Qt.ItemDataRole.UserRole - 1)
        self.engine.setToolTip(
            "Bawaan: kompresi gambar cepat. Lossless (qpdf): pembersihan tingkat objek tanpa kehilangan kualitas. "
            "Ghostscript: paling kuat untuk PDF hasil scan (memerlukan Ghostscript terpasang)."
        )
        row.addWidget(self.engine, 1)
        row.addWidget(QLabel("Tingkat kompresi"))
        self.level = QComboBox()
        for label, value in (
            ("Rendah", "low"),
            ("Disarankan", "recommended"),
            ("Tinggi", "high"),
            ("Maksimum", "maximum"),
        ):
            self.level.addItem(label, value)
        index = self.level.findData(default_level) if default_level else 1
        self.level.setCurrentIndex(index if index >= 0 else 1)
        row.addWidget(self.level, 1)
        self.level.currentTextChanged.connect(self.level_changed)
        self.process = QPushButton("Kompres PDF")
        self.process.setObjectName("success")
        self.process.clicked.connect(self.start)
        row.addWidget(self.process)
        self.layout.insertLayout(3, row)
        self.aggressive = QCheckBox("Kompresi agresif (file lebih kecil, halaman diubah menjadi gambar)")
        self.aggressive.setToolTip("Berguna untuk PDF yang sudah optimal. Seleksi teks dan pencarian akan hilang.")
        self.aggressive.setChecked(True)
        self.layout.insertWidget(4, self.aggressive)
        warning = QLabel("Mode agresif menurunkan kualitas gambar dan menghapus teks yang dapat dipilih/dicari.")
        warning.setObjectName("muted")
        self.layout.insertWidget(5, warning)
        self.layout.addStretch()

    def level_changed(self, level: str) -> None:
        if level == "Maksimum":
            self.aggressive.setChecked(True)

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
        self.status.setText(f"Dipilih: {info.path.name} · {info.pages} halaman · {info.size / 1048576:.2f} MB")

    def start(self) -> None:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        suggested = self.source.with_name(f"{self.source.stem}_compressed.pdf")
        output, _ = QFileDialog.getSaveFileName(self, "Simpan PDF terkompresi", str(suggested), "Berkas PDF (*.pdf)")
        if output:
            if self.aggressive.isChecked():
                answer = QMessageBox.warning(
                    self,
                    "Kompresi agresif",
                    "Halaman akan diubah menjadi gambar. Seleksi teks, tautan, formulir, dan pencarian mungkin hilang. Lanjutkan?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            self.run_job(
                compress_pdf,
                self.source,
                output,
                self.level.currentData(),
                aggressive=self.aggressive.isChecked(),
                engine=self.engine.currentData(),
                with_progress=True,
            )

    def _success(self, result: object) -> None:
        super()._success(result)
        if isinstance(result, CompressionResult) and self.source:
            HistoryStore().add(
                self.source.name, "Kompres PDF", result.original_size, result.compressed_size, str(result.output)
            )


class MergePage(ToolPage):
    def __init__(self) -> None:
        super().__init__("Gabung PDF", "Tambahkan dua PDF atau lebih, atur urutannya, lalu gabungkan dengan aman.")
        self.drop = DropZone("Seret beberapa file PDF di sini", multiple=True)
        self.layout.insertWidget(2, self.drop)
        self.drop.choose_requested.connect(self.choose)
        self.drop.files_dropped.connect(self.add_files)
        self.files = QListWidget()
        self.files.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.files.setMinimumHeight(150)
        self.layout.insertWidget(3, self.files)
        controls = QHBoxLayout()
        remove = QPushButton("Hapus yang Dipilih")
        remove.setObjectName("ghost")
        remove.clicked.connect(lambda: self.files.takeItem(self.files.currentRow()))
        merge = QPushButton("Gabung PDF")
        merge.setObjectName("success")
        merge.clicked.connect(self.start)
        controls.addWidget(remove)
        controls.addStretch()
        controls.addWidget(merge)
        self.layout.insertLayout(4, controls)
        self.layout.addStretch()

    def choose(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Pilih PDF", "", "Berkas PDF (*.pdf)")
        self.add_files(files)

    def add_files(self, files: list[str]) -> None:
        existing = {self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())}
        for filename in files:
            try:
                path = validate_pdf(filename).path
            except Exception as exc:
                self.status.setText(str(exc))
                continue
            if str(path) not in existing:
                self.files.addItem(path.name)
                self.files.item(self.files.count() - 1).setData(Qt.ItemDataRole.UserRole, str(path))
                existing.add(str(path))
        self.status.setText(f"{self.files.count()} file PDF dipilih")

    def start(self) -> None:
        sources = [self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())]
        if len(sources) < 2:
            QMessageBox.information(self, "Tambah PDF", "Tambahkan minimal dua file PDF.")
            return
        output, _ = QFileDialog.getSaveFileName(
            self, "Simpan PDF gabungan", str(Path(sources[0]).with_name("merged.pdf")), "Berkas PDF (*.pdf)"
        )
        if output:
            self.run_job(merge_pdfs, sources, output, with_progress=True)

    def _success(self, result: object) -> None:
        super()._success(result)
        if isinstance(result, Path):
            sources = [Path(self.files.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.files.count())]
            HistoryStore().add(
                f"{len(sources)} file",
                "Gabung PDF",
                sum(path.stat().st_size for path in sources if path.exists()),
                result.stat().st_size,
                str(result),
            )


class SplitPage(ToolPage):
    def __init__(self) -> None:
        super().__init__("Pecah PDF", "Pisahkan setiap halaman, buat potongan, atau ekstrak rentang halaman.")
        self.source: Path | None = None
        self.drop = DropZone()
        self.layout.insertWidget(2, self.drop)
        self.drop.choose_requested.connect(self.choose)
        self.drop.files_dropped.connect(self.set_files)
        row = QHBoxLayout()
        row.addWidget(QLabel("Mode"))
        self.mode = QComboBox()
        self.mode.addItems(["Setiap halaman", "Setiap N halaman", "Rentang halaman"])
        self.mode.currentTextChanged.connect(self.mode_changed)
        row.addWidget(self.mode)
        self.value = QComboBox()
        self.value.setEditable(True)
        self.value.addItem("1-3, 5")
        self.value.hide()
        row.addWidget(self.value, 1)
        self.count = QSpinBox()
        self.count.setRange(1, 9999)
        self.count.setValue(2)
        self.count.hide()
        row.addWidget(self.count)
        process = QPushButton("Pecah PDF")
        process.setObjectName("warning")
        process.clicked.connect(self.start)
        row.addWidget(process)
        self.layout.insertLayout(3, row)
        self.layout.addStretch()

    def mode_changed(self, mode: str) -> None:
        self.value.setVisible(mode == "Rentang halaman")
        self.count.setVisible(mode == "Setiap N halaman")

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
        mode = self.mode.currentText()
        if mode == "Rentang halaman":
            output, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan PDF hasil ekstrak",
                str(self.source.with_name(f"{self.source.stem}_extracted.pdf")),
                "Berkas PDF (*.pdf)",
            )
            if output:
                self.run_job(extract_range, self.source, output, self.value.currentText())
        else:
            folder = QFileDialog.getExistingDirectory(self, "Pilih folder tujuan", str(self.source.parent))
            if folder:
                self.run_job(split_every_n, self.source, folder, 1 if mode == "Setiap halaman" else self.count.value())

    def _success(self, result: object) -> None:
        super()._success(result)
        if self.source:
            outputs = list(result) if isinstance(result, list) else [Path(result)]
            HistoryStore().add(
                self.source.name,
                "Pecah / Ekstrak PDF",
                self.source.stat().st_size,
                sum(Path(path).stat().st_size for path in outputs),
                str(Path(outputs[0]).parent if len(outputs) > 1 else outputs[0]),
            )

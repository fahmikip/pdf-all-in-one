"""Operational Compress, Merge, and Split pages."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QThreadPool, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget,
    QMessageBox, QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from core.jobs.worker import FunctionWorker
from core.pdf.compressor import CompressionResult, compress_pdf
from core.pdf.merger import merge_pdfs
from core.pdf.splitter import extract_range, split_every_n
from core.utils.validation import validate_pdf
from core.utils.history import HistoryStore
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
        heading = QLabel(title); heading.setObjectName("title"); self.layout.addWidget(heading)
        subtitle = QLabel(description); subtitle.setObjectName("subtitle"); self.layout.addWidget(subtitle)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.hide(); self.layout.addWidget(self.progress)
        self.status = QLabel(""); self.status.setObjectName("muted"); self.layout.addWidget(self.status)
        self.open_button = QPushButton("Open Result"); self.open_button.setObjectName("primary"); self.open_button.hide()
        self.open_button.clicked.connect(self._open_result); self.layout.addWidget(self.open_button)

    def run_job(self, function: Callable[..., Any], *args: Any, with_progress: bool = False, **kwargs: Any) -> None:
        self.progress.setValue(0); self.progress.show(); self.open_button.hide(); self.status.setText("Processing…")
        worker = FunctionWorker(function, *args, with_progress=with_progress, **kwargs)
        worker.signals.progress.connect(self._progress)
        worker.signals.result.connect(self._success)
        worker.signals.error.connect(self._error)
        worker.signals.finished.connect(lambda: self.progress.hide())
        self.pool.start(worker)

    def _progress(self, value: int, detail: str) -> None:
        self.progress.setValue(value); self.status.setText(detail)

    def _success(self, result: object) -> None:
        if isinstance(result, CompressionResult):
            self.last_result = result.output
            if result.saved_bytes:
                self.status.setText(
                    f"Compression complete · {_format_size(result.original_size)} → "
                    f"{_format_size(result.compressed_size)} · Saved {result.reduction_percent:.1f}%"
                )
            else:
                self.status.setText("PDF is already optimized · A safe output copy was created")
        elif isinstance(result, list):
            self.last_result = Path(result[0]).parent if result else None
            self.status.setText(f"Split complete · {len(result)} files created")
        else:
            self.last_result = Path(result) if result else None
            self.status.setText("Operation completed successfully")
        self.progress.setValue(100)
        self.open_button.setText("Open Folder" if self.last_result and self.last_result.is_dir() else "Open Result")
        self.open_button.setVisible(self.last_result is not None)

    def _error(self, message: str, details: str) -> None:
        self.status.setText("Operation failed")
        dialog = QMessageBox(QMessageBox.Icon.Critical, "Something went wrong", message, parent=self)
        dialog.setInformativeText("Your original file was not changed."); dialog.setDetailedText(details); dialog.exec()

    def _open_result(self) -> None:
        if self.last_result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_result)))


class CompressPage(ToolPage):
    def __init__(self) -> None:
        super().__init__("Compress PDF", "Reduce PDF size locally without modifying the original file.")
        self.source: Path | None = None
        self.drop = DropZone(); self.layout.insertWidget(2, self.drop)
        self.drop.choose_requested.connect(self.choose); self.drop.files_dropped.connect(self.set_files)
        row = QHBoxLayout(); row.addWidget(QLabel("Compression level"))
        self.level = QComboBox(); self.level.addItems(["Low", "Recommended", "High", "Maximum"]); self.level.setCurrentText("Recommended"); row.addWidget(self.level, 1)
        self.process = QPushButton("Compress PDF"); self.process.setObjectName("primary"); self.process.clicked.connect(self.start); row.addWidget(self.process)
        self.layout.insertLayout(3, row)
        self.aggressive = QCheckBox("Aggressive compression (smaller file, converts pages to images)")
        self.aggressive.setToolTip("Useful for already optimized PDFs. Text selection and search will be lost.")
        self.layout.insertWidget(4, self.aggressive)
        warning = QLabel("Aggressive mode lowers image quality and removes selectable/searchable text.")
        warning.setObjectName("muted"); self.layout.insertWidget(5, warning); self.layout.addStretch()

    def choose(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose PDF", "", "PDF files (*.pdf)")
        if filename: self.set_files([filename])

    def set_files(self, files: list[str]) -> None:
        try: info = validate_pdf(files[0])
        except Exception as exc: self._error(str(exc), ""); return
        self.source = info.path; self.status.setText(f"Selected: {info.path.name} · {info.pages} pages · {info.size / 1048576:.2f} MB")

    def start(self) -> None:
        if not self.source: QMessageBox.information(self, "Select a PDF", "Choose a PDF first."); return
        suggested = self.source.with_name(f"{self.source.stem}_compressed.pdf")
        output, _ = QFileDialog.getSaveFileName(self, "Save compressed PDF", str(suggested), "PDF files (*.pdf)")
        if output:
            if self.aggressive.isChecked():
                answer = QMessageBox.warning(
                    self, "Aggressive compression",
                    "Pages will be converted to images. Text selection, links, forms, and search may be lost. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            self.run_job(
                compress_pdf, self.source, output, self.level.currentText().lower(),
                aggressive=self.aggressive.isChecked(), with_progress=True,
            )

    def _success(self, result: object) -> None:
        super()._success(result)
        if isinstance(result, CompressionResult) and self.source:
            HistoryStore().add(self.source.name, "Compress PDF", result.original_size, result.compressed_size, str(result.output))


class MergePage(ToolPage):
    def __init__(self) -> None:
        super().__init__("Merge PDF", "Add two or more PDFs, arrange their order, and combine them safely.")
        self.drop = DropZone("Drop multiple PDF files here", multiple=True); self.layout.insertWidget(2, self.drop)
        self.drop.choose_requested.connect(self.choose); self.drop.files_dropped.connect(self.add_files)
        self.files = QListWidget(); self.files.setDragDropMode(QListWidget.DragDropMode.InternalMove); self.files.setMinimumHeight(150); self.layout.insertWidget(3, self.files)
        controls = QHBoxLayout()
        remove = QPushButton("Remove Selected"); remove.clicked.connect(lambda: self.files.takeItem(self.files.currentRow()))
        merge = QPushButton("Merge PDF"); merge.setObjectName("primary"); merge.clicked.connect(self.start)
        controls.addWidget(remove); controls.addStretch(); controls.addWidget(merge); self.layout.insertLayout(4, controls); self.layout.addStretch()

    def choose(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Choose PDFs", "", "PDF files (*.pdf)")
        self.add_files(files)

    def add_files(self, files: list[str]) -> None:
        existing = {self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())}
        for filename in files:
            try: path = validate_pdf(filename).path
            except Exception as exc: self.status.setText(str(exc)); continue
            if str(path) not in existing:
                self.files.addItem(path.name); self.files.item(self.files.count() - 1).setData(Qt.ItemDataRole.UserRole, str(path)); existing.add(str(path))
        self.status.setText(f"{self.files.count()} PDF files selected")

    def start(self) -> None:
        sources = [self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())]
        if len(sources) < 2: QMessageBox.information(self, "Add PDFs", "Add at least two PDF files."); return
        output, _ = QFileDialog.getSaveFileName(self, "Save merged PDF", str(Path(sources[0]).with_name("merged.pdf")), "PDF files (*.pdf)")
        if output: self.run_job(merge_pdfs, sources, output, with_progress=True)

    def _success(self, result: object) -> None:
        super()._success(result)
        if isinstance(result, Path):
            sources = [Path(self.files.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.files.count())]
            HistoryStore().add(f"{len(sources)} files", "Merge PDF", sum(path.stat().st_size for path in sources if path.exists()), result.stat().st_size, str(result))


class SplitPage(ToolPage):
    def __init__(self) -> None:
        super().__init__("Split PDF", "Split every page, create chunks, or extract a page range.")
        self.source: Path | None = None
        self.drop = DropZone(); self.layout.insertWidget(2, self.drop); self.drop.choose_requested.connect(self.choose); self.drop.files_dropped.connect(self.set_files)
        row = QHBoxLayout(); row.addWidget(QLabel("Mode")); self.mode = QComboBox(); self.mode.addItems(["Every page", "Every N pages", "Page range"]); self.mode.currentTextChanged.connect(self.mode_changed); row.addWidget(self.mode)
        self.value = QComboBox(); self.value.setEditable(True); self.value.addItem("1-3, 5"); self.value.hide(); row.addWidget(self.value, 1)
        self.count = QSpinBox(); self.count.setRange(1, 9999); self.count.setValue(2); self.count.hide(); row.addWidget(self.count)
        process = QPushButton("Split PDF"); process.setObjectName("primary"); process.clicked.connect(self.start); row.addWidget(process)
        self.layout.insertLayout(3, row); self.layout.addStretch()

    def mode_changed(self, mode: str) -> None:
        self.value.setVisible(mode == "Page range"); self.count.setVisible(mode == "Every N pages")

    def choose(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose PDF", "", "PDF files (*.pdf)")
        if filename: self.set_files([filename])

    def set_files(self, files: list[str]) -> None:
        try: info = validate_pdf(files[0])
        except Exception as exc: self._error(str(exc), ""); return
        self.source = info.path; self.status.setText(f"Selected: {info.path.name} · {info.pages} pages")

    def start(self) -> None:
        if not self.source: QMessageBox.information(self, "Select a PDF", "Choose a PDF first."); return
        mode = self.mode.currentText()
        if mode == "Page range":
            output, _ = QFileDialog.getSaveFileName(self, "Save extracted PDF", str(self.source.with_name(f"{self.source.stem}_extracted.pdf")), "PDF files (*.pdf)")
            if output: self.run_job(extract_range, self.source, output, self.value.currentText())
        else:
            folder = QFileDialog.getExistingDirectory(self, "Choose output folder", str(self.source.parent))
            if folder: self.run_job(split_every_n, self.source, folder, 1 if mode == "Every page" else self.count.value())

    def _success(self, result: object) -> None:
        super()._success(result)
        if self.source:
            outputs = list(result) if isinstance(result, list) else [Path(result)]
            HistoryStore().add(self.source.name, "Split / Extract PDF", self.source.stat().st_size, sum(Path(path).stat().st_size for path in outputs), str(Path(outputs[0]).parent if len(outputs) > 1 else outputs[0]))

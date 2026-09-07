"""Extract text and images from a PDF."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QMessageBox,
    QProgressBar, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from core.jobs.worker import FunctionWorker
from core.pdf.extractor import extract_images, extract_text
from core.utils.history import HistoryStore
from core.utils.validation import validate_pdf
from ui.widgets.drop_zone import DropZone


class ExtractPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.worker: FunctionWorker | None = None
        self.pool = QThreadPool.globalInstance()
        layout = QVBoxLayout(self); layout.setContentsMargins(38, 30, 38, 30); layout.setSpacing(14)
        title = QLabel("Extract PDF"); title.setObjectName("title"); layout.addWidget(title)
        subtitle = QLabel("Pull selectable text or embedded images out of a PDF—entirely offline."); subtitle.setObjectName("subtitle"); layout.addWidget(subtitle)
        self.drop = DropZone(); self.drop.choose_requested.connect(self.choose); self.drop.files_dropped.connect(self.set_files); layout.addWidget(self.drop)
        mode_row = QHBoxLayout(); mode_row.addWidget(QLabel("Extract")); self.mode = QComboBox(); self.mode.addItems(["Text to .txt", "Images to files"]); self.mode.currentTextChanged.connect(self.mode_changed); mode_row.addWidget(self.mode, 1); layout.addLayout(mode_row)
        options = QHBoxLayout()
        self.format = QComboBox(); self.format.addItems(["PNG", "JPG", "WEBP"]); self.format.setVisible(False); options.addWidget(QLabel("Format")); options.addWidget(self.format)
        self.min_size = QSpinBox(); self.min_size.setRange(0, 100000); self.min_size.setSuffix(" px²"); self.min_size.setToolTip("Skip images smaller than this area"); self.min_size.setVisible(False); options.addWidget(QLabel("Min size")); options.addWidget(self.min_size)
        options.addStretch(); layout.addLayout(options)
        self.progress = QProgressBar(); self.progress.hide(); layout.addWidget(self.progress)
        self.status = QLabel("Choose a PDF to begin"); self.status.setObjectName("muted"); layout.addWidget(self.status)
        process = QPushButton("Extract"); process.setObjectName("primary"); process.clicked.connect(self.start); layout.addWidget(process)
        self.open_button = QPushButton("Open Folder"); self.open_button.hide(); self.open_button.clicked.connect(self.open_result); layout.addWidget(self.open_button)
        layout.addStretch()

    def mode_changed(self, mode: str) -> None:
        images = mode == "Images to files"
        self.format.setVisible(images); self.min_size.setVisible(images)
        self.status.setText("Choose a PDF to begin" if not self.source else self.status.text())

    def choose(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Choose PDF", "", "PDF files (*.pdf)")
        if name: self.set_files([name])

    def set_files(self, files: list[str]) -> None:
        try: info = validate_pdf(files[0])
        except Exception as exc: QMessageBox.warning(self, "Cannot open PDF", str(exc)); return
        self.source = info.path; self.status.setText(f"Selected: {info.path.name} · {info.pages} pages")

    def start(self) -> None:
        if not self.source: QMessageBox.information(self, "Select a PDF", "Choose a PDF first."); return
        if self.mode.currentText() == "Text to .txt":
            output, _ = QFileDialog.getSaveFileName(self, "Save extracted text", str(self.source.with_name(f"{self.source.stem}_text.txt")), "Text files (*.txt)")
            if not output: return
            self.run_job(extract_text, output)
        else:
            folder = QFileDialog.getExistingDirectory(self, "Choose output folder", str(self.source.parent))
            if not folder: return
            self.run_job(extract_images, folder, image_format=self.format.currentText().lower(), min_size=self.min_size.value())

    def run_job(self, function, target: str, *args, with_progress: bool = True, **kwargs) -> None:
        self.target = target
        self.progress.setValue(0); self.progress.show(); self.open_button.hide(); self.status.setText("Extracting…")
        worker = FunctionWorker(function, self.source, target, *args, with_progress=with_progress, **kwargs); self.worker = worker
        worker.signals.progress.connect(lambda value, detail: (self.progress.setValue(value), self.status.setText(detail)))
        worker.signals.result.connect(self.completed)
        worker.signals.error.connect(self.failed)
        worker.signals.finished.connect(lambda: (self.progress.hide(), setattr(self, "worker", None)))
        self.pool.start(worker)

    def completed(self, result: object) -> None:
        if not self.source: return
        if isinstance(result, list):
            count = len(result)
            output = result[0].parent
        else:
            count = 1
            output = Path(result).parent
        if count:
            self.status.setText(f"Extracted {count} item(s) → {output.name}")
            HistoryStore().add(self.source.name, f"Extract PDF ({self.mode.currentText()})", self.source.stat().st_size, 0, str(output))
        self.open_button.setText("Open Folder"); self.open_button.setVisible(True)

    def failed(self, message: str, details: str) -> None:
        self.status.setText("Extraction failed")
        dialog = QMessageBox(QMessageBox.Icon.Critical, "Something went wrong", message, parent=self)
        dialog.setDetailedText(details); dialog.exec()

    def open_result(self) -> None:
        if getattr(self, "target", None): QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.target).parent if not Path(self.target).is_dir() else self.target)))
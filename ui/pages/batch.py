"""Sequential, memory-conscious batch processing queue."""

from __future__ import annotations

from pathlib import Path

from core.jobs.queue import JobQueue, JobStatus
from core.jobs.worker import FunctionWorker
from core.pdf.compressor import CompressionResult, compress_pdf
from core.utils.history import HistoryStore
from core.utils.validation import validate_pdf
from PySide6.QtCore import Qt, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class BatchPage(QWidget):
    def __init__(self, default_level: str = "recommended") -> None:
        super().__init__()
        self.queue = JobQueue()
        self.paused = False
        self.worker = None
        self.output_dir: Path | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 27, 34, 27)
        title = QLabel("Proses Batch")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Proses banyak PDF secara berurutan untuk penggunaan memori yang stabil.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        options = QHBoxLayout()
        options.addWidget(QLabel("Tugas"))
        self.task = QComboBox()
        self.task.addItems(["Kompres PDF"])
        options.addWidget(self.task)
        options.addWidget(QLabel("Level"))
        self.level = QComboBox()
        for label, value in (
            ("Rendah", "low"),
            ("Disarankan", "recommended"),
            ("Tinggi", "high"),
            ("Maksimum", "maximum"),
        ):
            self.level.addItem(label, value)
        index = self.level.findData(default_level)
        self.level.setCurrentIndex(index if index >= 0 else 1)
        options.addWidget(self.level)
        add = QPushButton("Tambah PDF")
        add.setObjectName("ghost")
        add.clicked.connect(self.add_files)
        folder = QPushButton("Folder Output")
        folder.setObjectName("ghost")
        folder.clicked.connect(self.choose_output)
        options.addWidget(add)
        options.addWidget(folder)
        options.addStretch()
        layout.addLayout(options)
        self.output_label = QLabel("Output: di samping setiap file sumber")
        self.output_label.setObjectName("muted")
        layout.addWidget(self.output_label)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Nama File", "Tugas", "Status", "Progres", "Output", "Kesalahan"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        controls = QHBoxLayout()
        self.start_button = QPushButton("Mulai Antrean")
        self.start_button.setObjectName("success")
        self.start_button.clicked.connect(self.start)
        self.pause_button = QPushButton("Jeda Antrean")
        self.pause_button.setObjectName("warning")
        self.pause_button.clicked.connect(self.toggle_pause)
        cancel = QPushButton("Batalkan Tugas")
        cancel.setObjectName("danger")
        cancel.clicked.connect(self.cancel_selected)
        clear = QPushButton("Bersihkan Selesai")
        clear.setObjectName("ghost")
        clear.clicked.connect(self.clear_finished)
        for button in (self.start_button, self.pause_button, cancel, clear):
            controls.addWidget(button)
        controls.addStretch()
        layout.addLayout(controls)

    def choose_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Folder output batch")
        if folder:
            self.output_dir = Path(folder).resolve()
            self.output_label.setText(f"Output: {self.output_dir}")

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Tambah PDF", "", "Berkas PDF (*.pdf)")
        for filename in files:
            try:
                source = validate_pdf(filename).path
            except Exception as exc:
                QMessageBox.warning(self, "PDF dilewati", str(exc))
                continue
            folder = self.output_dir or source.parent
            output = folder / f"{source.stem}_compressed.pdf"
            self.queue.add(source, "Kompres PDF", output)
        self.refresh()

    def refresh(self) -> None:
        jobs = self.queue.snapshot()
        self.table.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            values = (job.source.name, job.task, job.status.value, f"{job.progress}%", str(job.output), job.error)
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, job.id)
        self.table.resizeColumnsToContents()

    def start(self) -> None:
        self.paused = False
        self.pause_button.setText("Jeda Antrean")
        self._run_next()

    def _run_next(self) -> None:
        if self.paused or self.worker is not None:
            return
        job = self.queue.next_waiting()
        if not job:
            self.start_button.setText("Mulai Antrean")
            return
        self.queue.update(job.id, status=JobStatus.PROCESSING, progress=5)
        self.refresh()
        worker = FunctionWorker(compress_pdf, job.source, job.output, self.level.currentData(), with_progress=True)
        self.worker = worker
        worker.signals.progress.connect(lambda value, detail, job_id=job.id: self.update_progress(job_id, value))
        worker.signals.result.connect(lambda result, job_id=job.id: self.completed(job_id, result))
        worker.signals.error.connect(lambda message, details, job_id=job.id: self.failed(job_id, message))
        worker.signals.finished.connect(self.finished)
        QThreadPool.globalInstance().start(worker)

    def completed(self, job_id: str, result: object) -> None:
        job = self.queue.get(job_id)
        if not job:
            return
        if job.status == JobStatus.CANCELLED:
            if isinstance(result, CompressionResult):
                result.output.unlink(missing_ok=True)
            return
        self.queue.update(job_id, status=JobStatus.COMPLETED, progress=100)
        if isinstance(result, CompressionResult):
            HistoryStore().add(
                job.source.name, "Kompres PDF Batch", result.original_size, result.compressed_size, str(result.output)
            )
        self.refresh()

    def update_progress(self, job_id: str, value: int) -> None:
        job = self.queue.get(job_id)
        if job and job.status == JobStatus.PROCESSING:
            self.queue.update(job_id, progress=value)
            self.refresh()

    def failed(self, job_id: str, message: str) -> None:
        job = self.queue.get(job_id)
        if job and job.status != JobStatus.CANCELLED:
            self.queue.update(job_id, status=JobStatus.FAILED, error=message)
        self.refresh()

    def finished(self) -> None:
        self.worker = None
        self.refresh()
        QTimer.singleShot(0, self._run_next)

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.setText("Lanjutkan Antrean" if self.paused else "Jeda Antrean")
        if not self.paused:
            self._run_next()

    def cancel_selected(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.queue.cancel(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
            self.refresh()

    def clear_finished(self) -> None:
        self.queue.clear_finished()
        self.refresh()

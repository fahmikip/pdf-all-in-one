"""Permanent redaction and annotation workspace."""

from __future__ import annotations

from pathlib import Path

from core.jobs.worker import FunctionWorker
from core.pdf.annotations import annotate_pdf
from core.pdf.redaction import find_text, redact_text, replace_text
from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class RedactPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.pool = QThreadPool.globalInstance()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 28)
        title = QLabel("Redaksi & Anotasi")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Hapus isi sensitif secara permanen atau tambahkan sorotan dan catatan ke PDF.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        picker = QHBoxLayout()
        self.file_label = QLabel("Belum ada PDF dipilih")
        choose = QPushButton("Pilih PDF")
        choose.setObjectName("ghost")
        choose.clicked.connect(self.choose)
        picker.addWidget(self.file_label, 1)
        picker.addWidget(choose)
        layout.addLayout(picker)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        redact = QWidget()
        red_layout = QVBoxLayout(redact)
        warning = QLabel(
            "Redaksi menghapus teks dan konten yang tertutup dari salinan PDF. Proses ini tidak dapat dibatalkan pada file hasil."
        )
        warning.setWordWrap(True)
        warning.setObjectName("muted")
        red_layout.addWidget(warning)
        form = QFormLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Contoh: nomor rekening atau nama")
        form.addRow("Teks sensitif", self.query)
        red_layout.addLayout(form)
        controls = QHBoxLayout()
        search = QPushButton("Cari kecocokan")
        search.setObjectName("ghost")
        search.clicked.connect(self.search)
        remove = QPushButton("Hapus permanen…")
        remove.setObjectName("danger")
        remove.clicked.connect(self.redact)
        controls.addWidget(search)
        controls.addWidget(remove)
        controls.addStretch()
        red_layout.addLayout(controls)
        self.matches = QListWidget()
        red_layout.addWidget(self.matches, 1)
        replacement_row = QHBoxLayout()
        self.replacement = QLineEdit()
        self.replacement.setPlaceholderText("Ganti dengan teks ini (opsional)")
        replace = QPushButton("Ganti teks…")
        replace.setObjectName("warning")
        replace.clicked.connect(self.replace)
        replacement_row.addWidget(self.replacement, 1)
        replacement_row.addWidget(replace)
        red_layout.addLayout(replacement_row)
        tabs.addTab(redact, "Redaksi permanen")
        annotate = QWidget()
        ann_layout = QVBoxLayout(annotate)
        ann_layout.addWidget(
            QLabel("Sorot frasa yang cocok di semua halaman dan/atau sisipkan catatan di halaman pertama.")
        )
        self.highlight_query = QLineEdit()
        self.highlight_query.setPlaceholderText("Frasa untuk disorot (opsional)")
        ann_layout.addWidget(self.highlight_query)
        self.note = QTextEdit()
        self.note.setPlaceholderText("Catatan PDF (opsional)")
        self.note.setMaximumHeight(110)
        ann_layout.addWidget(self.note)
        save_note = QPushButton("Simpan anotasi sebagai PDF baru")
        save_note.setObjectName("success")
        save_note.clicked.connect(self.annotate)
        ann_layout.addWidget(save_note)
        ann_layout.addStretch()
        tabs.addTab(annotate, "Sorot & catatan")
        self.status = QLabel("")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)

    def choose(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Pilih PDF", "", "Berkas PDF (*.pdf)")
        if name:
            self.source = Path(name).resolve()
            self.file_label.setText(self.source.name)
            self.matches.clear()

    def search(self) -> None:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        try:
            found = find_text(self.source, self.query.text())
        except Exception as exc:
            QMessageBox.warning(self, "Pencarian gagal", str(exc))
            return
        self.matches.clear()
        for match in found:
            self.matches.addItem(f"Halaman {match['page'] + 1} · {match['text']}")
        self.status.setText(f"{len(found)} kecocokan ditemukan. Redaksi akan menghapus semuanya.")

    def redact(self) -> None:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        if not self.matches.count():
            self.search()
        if not self.matches.count():
            return
        answer = QMessageBox.warning(
            self,
            "Konfirmasi redaksi permanen",
            f"Semua {self.matches.count()} kecocokan teks akan dihapus dari salinan baru. Tindakan ini tidak dapat dibatalkan. Lanjutkan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        output, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan PDF yang sudah diredaksi",
            str(self.source.with_name(f"{self.source.stem}_redacted.pdf")),
            "PDF (*.pdf)",
        )
        if output:
            worker = FunctionWorker(redact_text, self.source, output, self.query.text())
            worker.signals.result.connect(self.saved)
            worker.signals.error.connect(self.failed)
            self.pool.start(worker)

    def annotate(self) -> None:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        output, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan PDF beranotasi",
            str(self.source.with_name(f"{self.source.stem}_annotated.pdf")),
            "PDF (*.pdf)",
        )
        if output:
            worker = FunctionWorker(
                annotate_pdf, self.source, output, query=self.highlight_query.text(), note=self.note.toPlainText()
            )
            worker.signals.result.connect(self.saved)
            worker.signals.error.connect(self.failed)
            self.pool.start(worker)

    def replace(self) -> None:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        query = self.query.text().strip()
        if not query:
            QMessageBox.information(self, "Masukkan teks", "Masukkan teks yang ingin diganti lalu cari kecocokannya.")
            return
        if not self.matches.count():
            self.search()
        if not self.matches.count():
            return
        output, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan PDF hasil penggantian",
            str(self.source.with_name(f"{self.source.stem}_replaced.pdf")),
            "PDF (*.pdf)",
        )
        if output:
            worker = FunctionWorker(replace_text, self.source, output, query, self.replacement.text())
            worker.signals.result.connect(self.saved)
            worker.signals.error.connect(self.failed)
            self.pool.start(worker)

    def saved(self, result: object) -> None:
        output = Path(result)
        self.status.setText(f"Tersimpan: {output.name}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

    def failed(self, message: str, _details: str) -> None:
        QMessageBox.critical(self, "Operasi gagal", message)

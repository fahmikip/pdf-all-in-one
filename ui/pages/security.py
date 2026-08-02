"""Protect and unlock PDF interface."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QCheckBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QTabWidget, QVBoxLayout, QWidget

from core.jobs.worker import FunctionWorker
from core.pdf.security import password_strength, protect_pdf, unlock_pdf
from core.utils.validation import validate_pdf


class SecurityPage(QWidget):
    def __init__(self) -> None:
        super().__init__(); self.source: Path | None = None; self.worker = None
        layout = QVBoxLayout(self); layout.setContentsMargins(38, 30, 38, 30)
        title = QLabel("PDF Security"); title.setObjectName("title"); layout.addWidget(title)
        subtitle = QLabel("Protect documents or remove encryption when you know the password."); subtitle.setObjectName("subtitle"); layout.addWidget(subtitle)
        row = QHBoxLayout(); self.source_label = QLabel("No PDF selected"); choose = QPushButton("Choose PDF"); choose.clicked.connect(self.choose); row.addWidget(self.source_label, 1); row.addWidget(choose); layout.addLayout(row)
        tabs = QTabWidget(); layout.addWidget(tabs); protect = QWidget(); form = QFormLayout(protect)
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.EchoMode.Password); self.password.textChanged.connect(self.update_strength); form.addRow("Open password", self.password)
        self.confirm = QLineEdit(); self.confirm.setEchoMode(QLineEdit.EchoMode.Password); form.addRow("Confirm password", self.confirm)
        self.strength = QProgressBar(); self.strength.setRange(0, 100); form.addRow("Strength", self.strength)
        self.strength_label = QLabel("Weak"); form.addRow("", self.strength_label)
        self.printing = QCheckBox("Allow printing"); self.printing.setChecked(True); form.addRow(self.printing)
        self.copying = QCheckBox("Allow copying and accessibility"); self.copying.setChecked(True); form.addRow(self.copying)
        self.editing = QCheckBox("Allow editing"); form.addRow(self.editing)
        button = QPushButton("Protect PDF"); button.setObjectName("primary"); button.clicked.connect(self.protect); form.addRow(button); tabs.addTab(protect, "Protect PDF")
        unlock = QWidget(); unlock_form = QFormLayout(unlock); self.unlock_password = QLineEdit(); self.unlock_password.setEchoMode(QLineEdit.EchoMode.Password); unlock_form.addRow("Current password", self.unlock_password)
        unlock_button = QPushButton("Unlock PDF"); unlock_button.setObjectName("primary"); unlock_button.clicked.connect(self.unlock); unlock_form.addRow(unlock_button); tabs.addTab(unlock, "Unlock PDF")
        self.status = QLabel("Passwords are never stored or logged."); self.status.setObjectName("muted"); layout.addWidget(self.status); layout.addStretch()

    def choose(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Choose PDF", "", "PDF files (*.pdf)")
        if not name: return
        try: info = validate_pdf(name, allow_encrypted=True)
        except Exception as exc: QMessageBox.warning(self, "Cannot open PDF", str(exc)); return
        self.source = info.path; self.source_label.setText(f"{info.path.name} · {'Protected' if info.encrypted else 'Not protected'}")

    def update_strength(self, value: str) -> None:
        score, label = password_strength(value); self.strength.setValue(score); self.strength_label.setText(label)

    def _output(self, suffix: str) -> str:
        if not self.source: QMessageBox.information(self, "Choose PDF", "Choose a PDF first."); return ""
        name, _ = QFileDialog.getSaveFileName(self, "Save PDF", str(self.source.with_name(f"{self.source.stem}_{suffix}.pdf")), "PDF files (*.pdf)"); return name

    def protect(self) -> None:
        if self.password.text() != self.confirm.text(): QMessageBox.warning(self, "Passwords do not match", "Enter the same password twice."); return
        if not self.password.text(): QMessageBox.warning(self, "Password required", "Enter an open password."); return
        output = self._output("protected")
        if output: self._run(protect_pdf, output, self.password.text(), allow_printing=self.printing.isChecked(), allow_copying=self.copying.isChecked(), allow_editing=self.editing.isChecked())

    def unlock(self) -> None:
        if not self.unlock_password.text(): QMessageBox.warning(self, "Password required", "Enter the current PDF password."); return
        output = self._output("unlocked")
        if output: self._run(unlock_pdf, output, self.unlock_password.text())

    def _run(self, function, output: str, *args, **kwargs) -> None:
        if not self.source: return
        self.status.setText("Processing…"); worker = FunctionWorker(function, self.source, output, *args, **kwargs); self.worker = worker
        worker.signals.result.connect(self.completed); worker.signals.error.connect(lambda message, details: QMessageBox.critical(self, "Security operation failed", message)); worker.signals.finished.connect(lambda: setattr(self, "worker", None)); QThreadPool.globalInstance().start(worker)

    def completed(self, result: object) -> None:
        output = Path(result); self.status.setText(f"Saved: {output.name}"); QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

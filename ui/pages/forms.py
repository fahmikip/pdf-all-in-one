"""Fill PDF form fields and add visual signatures."""
from __future__ import annotations

from pathlib import Path

import fitz
from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from core.jobs.worker import FunctionWorker
from core.pdf.forms import fill_pdf_form, list_form_fields, sign_pdf
from core.utils.history import HistoryStore
from core.utils.validation import validate_pdf

SIGN_WIDTH = 200.0
SIGN_HEIGHT = 70.0


class FormsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.worker: FunctionWorker | None = None
        self.pool = QThreadPool.globalInstance()
        layout = QVBoxLayout(self); layout.setContentsMargins(38, 30, 38, 30); layout.setSpacing(14)
        title = QLabel("PDF Forms & Signature"); title.setObjectName("title"); layout.addWidget(title)
        subtitle = QLabel("Fill out interactive PDF fields or stamp a visual signature—completely offline."); subtitle.setObjectName("subtitle"); layout.addWidget(subtitle)
        tabs = QTabWidget(); layout.addWidget(tabs, 1)
        tabs.addTab(self._fill_tab(), "Fill Form")
        tabs.addTab(self._sign_tab(), "Sign Document")
        self.status = QLabel("Choose a PDF to begin"); self.status.setObjectName("muted"); layout.addWidget(self.status)

    def _choose_source_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); self.source_label = QLabel("No PDF selected"); choose = QPushButton("Choose PDF"); choose.clicked.connect(self.choose); row.addWidget(self.source_label, 1); row.addWidget(choose)
        return row

    def _fill_tab(self) -> QWidget:
        tab = QWidget(); box = QVBoxLayout(tab); box.addLayout(self._choose_source_row())
        self.fields = QTableWidget(0, 5)
        self.fields.setHorizontalHeaderLabels(["Page", "Field Name", "Type", "Current Value", "New Value"])
        self.fields.horizontalHeader().setStretchLastSection(True)
        self.fields.verticalHeader().setVisible(False)
        box.addWidget(self.fields, 1)
        actions = QHBoxLayout(); self.fill_progress = QProgressBar(); self.fill_progress.hide(); actions.addWidget(self.fill_progress, 1)
        save = QPushButton("Save Filled PDF"); save.setObjectName("primary"); save.clicked.connect(self.save_filled); actions.addWidget(save)
        box.addLayout(actions)
        hint = QLabel("Set values in the New Value column, then save a copy. The original is never modified."); hint.setObjectName("muted"); box.addWidget(hint)
        return tab

    def _sign_tab(self) -> QWidget:
        tab = QWidget(); box = QVBoxLayout(tab); box.addLayout(self._choose_source_row())
        image_row = QHBoxLayout(); self.image_label = QLabel("No signature image chosen"); choose = QPushButton("Choose Signature Image"); choose.clicked.connect(self.choose_image); image_row.addWidget(self.image_label, 1); image_row.addWidget(choose); box.addLayout(image_row)
        controls = QHBoxLayout()
        self.page = QSpinBox(); self.page.setRange(1, 999); self.page.setValue(1); controls.addWidget(QLabel("Page")); controls.addWidget(self.page)
        self.position = QComboBox(); self.position.addItems(["Bottom-left", "Bottom-right", "Top-left", "Top-right"]); controls.addWidget(QLabel("Position")); controls.addWidget(self.position)
        controls.addStretch(); box.addLayout(controls)
        fields = QHBoxLayout(); self.name = QLineEdit(); self.name.setPlaceholderText("Signer name (optional)"); self.role = QLineEdit(); self.role.setPlaceholderText("Role, e.g. Manager (optional)"); fields.addWidget(self.name, 1); fields.addWidget(self.role, 1); box.addLayout(fields)
        actions = QHBoxLayout(); self.sign_progress = QProgressBar(); self.sign_progress.hide(); actions.addWidget(self.sign_progress, 1)
        sign = QPushButton("Sign PDF"); sign.setObjectName("primary"); sign.clicked.connect(self.save_signed); actions.addWidget(sign); box.addLayout(actions)
        hint = QLabel("Signing adds a visual signature stamp; it does not create a cryptographic signature."); hint.setObjectName("muted"); box.addWidget(hint)
        return tab

    def choose(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Choose PDF", "", "PDF files (*.pdf)")
        if not name: return
        try: info = validate_pdf(name)
        except Exception as exc: QMessageBox.warning(self, "Cannot open PDF", str(exc)); return
        self.source = info.path; self.source_label.setText(f"{info.path.name} · {info.pages} pages")
        with fitz.open(self.source) as doc:
            self.page_size = (doc[0].rect.width, doc[0].rect.height) if doc.page_count else (595.0, 842.0)
        self.page.setMaximum(info.pages)
        self.load_fields()

    def load_fields(self) -> None:
        if not self.source: return
        try: fields = list_form_fields(self.source)
        except Exception as exc: QMessageBox.warning(self, "No form fields", str(exc)); return
        self.fields.setRowCount(len(fields))
        for row, field in enumerate(fields):
            self.fields.setItem(row, 0, QTableWidgetItem(str(field["page"])))
            self.fields.setItem(row, 1, QTableWidgetItem(str(field["name"])))
            self.fields.setItem(row, 2, QTableWidgetItem(str(field["type"])))
            self.fields.setItem(row, 3, QTableWidgetItem(str(field["value"])))
            self.fields.setItem(row, 4, QTableWidgetItem(""))
        self.fields.resizeColumnsToContents()
        self.status.setText(f"Found {len(fields)} form field(s)")

    def choose_image(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Choose signature image", "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not name: return
        self.image = Path(name); self.image_label.setText(self.image.name)

    def _updates(self) -> dict[str, object]:
        updates: dict[str, object] = {}
        for row in range(self.fields.rowCount()):
            name = self.fields.item(row, 1).text().strip()
            value_item = self.fields.item(row, 4)
            if not name: continue
            value = value_item.text().strip() if value_item else ""
            if not value: continue
            if self.fields.item(row, 2).text() == "CheckBox":
                updates[name] = value.lower() in ("1", "x", "yes", "on", "true")
            else:
                updates[name] = value
        return updates

    def save_filled(self) -> None:
        if not self.source: QMessageBox.information(self, "Select a PDF", "Choose a PDF first."); return
        updates = self._updates()
        if not updates: QMessageBox.information(self, "Enter values", "Enter a New Value for at least one field."); return
        output, _ = QFileDialog.getSaveFileName(self, "Save filled PDF", str(self.source.with_name(f"{self.source.stem}_filled.pdf")), "PDF files (*.pdf)")
        if not output: return
        self.target = Path(output)
        self._run_job("fill", fill_pdf_form, updates)

    def save_signed(self) -> None:
        if not self.source: QMessageBox.information(self, "Select a PDF", "Choose a PDF first."); return
        image = getattr(self, "image", None)
        if image is None and not self.name.text() and not self.role.text():
            QMessageBox.information(self, "Signature required", "Choose a signature image or enter a signer name."); return
        output, _ = QFileDialog.getSaveFileName(self, "Save signed PDF", str(self.source.with_name(f"{self.source.stem}_signed.pdf")), "PDF files (*.pdf)")
        if not output: return
        self.target = Path(output)
        width, height = getattr(self, "page_size", (595.0, 842.0))
        margin = 40.0
        left, top, right, bottom = 0.0, 0.0, SIGN_WIDTH, SIGN_HEIGHT
        bottom_y = height - margin
        right_x = width - margin
        left_x, top_y = margin, height - margin - SIGN_HEIGHT
        positions = {
            "Bottom-left": (left_x, top_y, left_x + SIGN_WIDTH, top_y + SIGN_HEIGHT),
            "Bottom-right": (right_x - SIGN_WIDTH, bottom_y - SIGN_HEIGHT, right_x, bottom_y),
            "Top-left": (margin, margin, margin + SIGN_WIDTH, margin + SIGN_HEIGHT),
            "Top-right": (right_x - SIGN_WIDTH, margin, right_x, margin + SIGN_HEIGHT),
        }
        rect = positions[self.position.currentText()]
        self._run_job("sign", sign_pdf, image_path=image, page_number=self.page.value(), rect=rect, name=self.name.text().strip(), role=self.role.text().strip())

    def _run_job(self, action: str, function, *args, **kwargs) -> None:
        progress = self.fill_progress if action == "fill" else self.sign_progress
        self.status.setText("Processing…")
        progress.setValue(0); progress.show()
        worker = FunctionWorker(function, self.source, self.target, *args, with_progress=True, **kwargs); self.worker = worker
        worker.signals.progress.connect(lambda value, detail: (progress.setValue(value), self.status.setText(detail)))
        worker.signals.result.connect(lambda result: self.completed(action, result))
        worker.signals.error.connect(lambda message, details: self.failed(message, details))
        worker.signals.finished.connect(lambda: (progress.hide(), setattr(self, "worker", None)))
        self.pool.start(worker)

    def completed(self, action: str, result: object) -> None:
        output = Path(result)
        self.status.setText(f"Saved: {output.name}")
        HistoryStore().add(self.source.name, "Fill Form" if action == "fill" else "Sign PDF", self.source.stat().st_size, 0, str(output))
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

    def failed(self, message: str, details: str) -> None:
        self.status.setText("Operation failed")
        dialog = QMessageBox(QMessageBox.Icon.Critical, "Something went wrong", message, parent=self)
        dialog.setDetailedText(details); dialog.exec()
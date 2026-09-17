"""Repair & Optimize: recover damaged files and produce Fast Web View copies."""

from __future__ import annotations

from pathlib import Path

from core.pdf.repair import linearize_pdf, repair_pdf
from core.utils.history import HistoryStore
from core.utils.validation import validate_pdf
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.pages.pdf_tools import ToolPage


class RepairPage(ToolPage):
    def __init__(self) -> None:
        super().__init__(
            "Repair & Optimize",
            "Recover files that will not open, or prepare copies that load faster over the web.",
        )
        self.sources: dict[str, Path | None] = {"repair": None, "linearize": None}
        self.action = ""
        tabs = QTabWidget()
        tabs.addTab(self._repair_tab(), "Repair PDF")
        tabs.addTab(self._linearize_tab(), "Fast Web View")
        self.layout.insertWidget(2, tabs)
        self.layout.addStretch()

    def _choose_row(self, key: str, message: str) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(message)
        label.setObjectName("muted")
        choose = QPushButton("Choose PDF")
        choose.setObjectName("ghost")
        choose.clicked.connect(lambda: self.choose(key, label))
        row.addWidget(label, 1)
        row.addWidget(choose)
        return row

    def _repair_tab(self) -> QWidget:
        tab = QWidget()
        box = QVBoxLayout(tab)
        box.addLayout(self._choose_row("repair", "No PDF selected"))
        run = QPushButton("Repair & Save")
        run.setObjectName("warning")
        run.clicked.connect(self.start_repair)
        box.addWidget(run)
        hint = QLabel(
            "Repair rebuilds the file structure with qpdf (or the built-in engine). "
            "Severe container corruption may still be unrecoverable."
        )
        hint.setObjectName("muted")
        box.addWidget(hint)
        box.addStretch()
        return tab

    def _linearize_tab(self) -> QWidget:
        tab = QWidget()
        box = QVBoxLayout(tab)
        box.addLayout(self._choose_row("linearize", "No PDF selected"))
        run = QPushButton("Linearize PDF")
        run.setObjectName("success")
        run.clicked.connect(self.start_linearize)
        box.addWidget(run)
        hint = QLabel(
            "Linearized (Fast Web View) files display page by page while downloading, perfect for sharing online."
        )
        hint.setObjectName("muted")
        box.addWidget(hint)
        box.addStretch()
        return tab

    def choose(self, key: str, label: QLabel) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Choose PDF" if key == "linearize" else "Choose PDF to repair", "", "PDF files (*.pdf)"
        )
        if not name:
            return
        path = Path(name)
        if key == "linearize":
            try:
                info = validate_pdf(path)
            except Exception as exc:
                QMessageBox.warning(self, "Cannot open PDF", str(exc))
                return
            self.sources[key] = info.path
            label.setText(f"{info.path.name} · {info.pages} pages")
        else:
            self.sources[key] = path
            label.setText(path.name)

    def start_repair(self) -> None:
        source = self.sources.get("repair")
        if not source:
            QMessageBox.information(self, "Select a PDF", "Choose a PDF first.")
            return
        output, _ = QFileDialog.getSaveFileName(
            self, "Save repaired PDF", str(source.with_name(f"{source.stem}_repaired.pdf")), "PDF files (*.pdf)"
        )
        if not output:
            return
        self.action = "repair"
        self.source = source
        self.run_job(repair_pdf, source, output, with_progress=True)

    def start_linearize(self) -> None:
        source = self.sources.get("linearize")
        if not source:
            QMessageBox.information(self, "Select a PDF", "Choose a PDF first.")
            return
        output, _ = QFileDialog.getSaveFileName(
            self, "Save linearized PDF", str(source.with_name(f"{source.stem}_web.pdf")), "PDF files (*.pdf)"
        )
        if not output:
            return
        self.action = "linearize"
        self.source = source
        self.run_job(linearize_pdf, source, output, with_progress=True)

    def _success(self, result: object) -> None:
        super()._success(result)
        output = Path(result) if isinstance(result, Path) else None
        if output is None or self.source is None:
            return
        if self.action == "repair":
            self.status.setText(f"Repaired: {output.name}")
            HistoryStore().add(
                self.source.name,
                "Repair PDF",
                self.source.stat().st_size,
                output.stat().st_size,
                str(output),
            )
        elif self.action == "linearize":
            self.status.setText(f"Linearized: {output.name}")
            HistoryStore().add(
                self.source.name,
                "Fast Web View",
                self.source.stat().st_size,
                output.stat().st_size,
                str(output),
            )

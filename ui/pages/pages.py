"""Page Tools: remove blank pages, resize to standard page sizes, and create new blank PDFs."""

from __future__ import annotations

from pathlib import Path

from core.pdf.pages import PAGE_SIZES, create_blank_pdf, remove_blank_pages, resize_pages
from core.utils.history import HistoryStore
from core.utils.validation import validate_pdf
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.pages.pdf_tools import ToolPage


class PageToolsPage(ToolPage):
    def __init__(self) -> None:
        super().__init__("Page Tools", "Clean up blank pages, re-fit pages to standard sizes, or start a new document.")
        self.sources: dict[str, Path | None] = {"blank": None, "resize": None}
        self.source_pages: dict[str, int] = {}
        self.action: tuple[str, str] = ("", "")
        tabs = QTabWidget()
        tabs.addTab(self._blank_tab(), "Remove Blank Pages")
        tabs.addTab(self._resize_tab(), "Resize Pages")
        tabs.addTab(self._new_tab(), "New PDF")
        self.layout.insertWidget(2, tabs)
        self.layout.addStretch()

    def _choose_row(self, key: str) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel("No PDF selected")
        label.setObjectName("muted")
        choose = QPushButton("Choose PDF")
        choose.setObjectName("ghost")
        choose.clicked.connect(lambda: self.choose(key, label))
        row.addWidget(label, 1)
        row.addWidget(choose)
        return row

    def _blank_tab(self) -> QWidget:
        tab = QWidget()
        box = QVBoxLayout(tab)
        box.addLayout(self._choose_row("blank"))
        self.blank_count = QLabel("")
        self.blank_count.setObjectName("muted")
        box.addWidget(self.blank_count)
        controls = QHBoxLayout()
        detect = QPushButton("Preview Blank Pages")
        detect.setObjectName("ghost")
        detect.clicked.connect(self.preview_blank)
        controls.addWidget(detect)
        controls.addStretch()
        run = QPushButton("Remove Blank Pages")
        run.setObjectName("danger")
        run.clicked.connect(self.start_blank)
        controls.addWidget(run)
        box.addLayout(controls)
        hint = QLabel("A blank page has no text, images, or drawings. The original file is never changed.")
        hint.setObjectName("muted")
        box.addWidget(hint)
        box.addStretch()
        return tab

    def _resize_tab(self) -> QWidget:
        tab = QWidget()
        box = QVBoxLayout(tab)
        box.addLayout(self._choose_row("resize"))
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Page size"))
        self.target_size = QComboBox()
        self.target_size.addItems(list(PAGE_SIZES))
        controls.addWidget(self.target_size, 1)
        controls.addWidget(QLabel("Fit"))
        self.fit_mode = QComboBox()
        self.fit_mode.addItems(["Fit", "Fill", "Stretch"])
        self.fit_mode.setToolTip(
            "Fit: whole page visible. Fill: cover the page (crops edges). Stretch: distort to fill the page."
        )
        controls.addWidget(self.fit_mode, 1)
        controls.addWidget(QLabel("Margin"))
        self.resample_margin = QSpinBox()
        self.resample_margin.setRange(0, 200)
        self.resample_margin.setSuffix(" pt")
        controls.addWidget(self.resample_margin, 1)
        run = QPushButton("Resize Pages")
        run.setObjectName("success")
        run.clicked.connect(self.start_resize)
        controls.addWidget(run)
        box.addLayout(controls)
        hint = QLabel("Content is scaled to the new page; original files are left untouched.")
        hint.setObjectName("muted")
        box.addWidget(hint)
        box.addStretch()
        return tab

    def _new_tab(self) -> QWidget:
        tab = QWidget()
        box = QVBoxLayout(tab)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Page size"))
        self.new_size = QComboBox()
        self.new_size.addItems(list(PAGE_SIZES))
        controls.addWidget(self.new_size, 1)
        controls.addWidget(QLabel("Pages"))
        self.new_pages = QSpinBox()
        self.new_pages.setRange(1, 5000)
        self.new_pages.setValue(1)
        controls.addWidget(self.new_pages, 1)
        run = QPushButton("Create PDF")
        run.setObjectName("success")
        run.clicked.connect(self.start_new)
        controls.addWidget(run)
        box.addLayout(controls)
        hint = QLabel("Creates a new empty PDF you can later fill using the Insert & Edit editor.")
        hint.setObjectName("muted")
        box.addWidget(hint)
        box.addStretch()
        return tab

    def choose(self, key: str, label: QLabel) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Choose PDF", "", "PDF files (*.pdf)")
        if not name:
            return
        try:
            info = validate_pdf(name)
        except Exception as exc:
            QMessageBox.warning(self, "Cannot open PDF", str(exc))
            return
        self.sources[key] = info.path
        self.source_pages[key] = info.pages
        label.setText(f"{info.path.name} · {info.pages} pages")

    def preview_blank(self) -> None:
        source = self.sources.get("blank")
        if not source:
            QMessageBox.information(self, "Select a PDF", "Choose a PDF first.")
            return
        self.status.setText("Scanning for blank pages…")
        from core.pdf.pages import detect_blank_pages

        self.run_job(detect_blank_pages, source, with_progress=True)
        self.action = ("detect", "")

    def start_blank(self) -> None:
        source = self.sources.get("blank")
        if not source:
            QMessageBox.information(self, "Select a PDF", "Choose a PDF first.")
            return
        output, _ = QFileDialog.getSaveFileName(
            self, "Save cleaned PDF", str(source.with_name(f"{source.stem}_clean.pdf")), "PDF files (*.pdf)"
        )
        if not output:
            return
        self.action = ("blank", "")
        self.source = source
        self.run_job(remove_blank_pages, source, output, with_progress=True)

    def start_resize(self) -> None:
        source = self.sources.get("resize")
        if not source:
            QMessageBox.information(self, "Select a PDF", "Choose a PDF first.")
            return
        output, _ = QFileDialog.getSaveFileName(
            self, "Save resized PDF", str(source.with_name(f"{source.stem}_{self.target_size.currentText().replace(' ', '_')}.pdf")),
            "PDF files (*.pdf)",
        )
        if not output:
            return
        self.action = ("resize", self.target_size.currentText())
        self.source = source
        self.run_job(
            resize_pages,
            source,
            output,
            target=self.target_size.currentText(),
            mode=self.fit_mode.currentText(),
            margin=float(self.resample_margin.value()),
            with_progress=True,
        )

    def start_new(self) -> None:
        suggested = str((Path.cwd() / "new_document.pdf").expanduser())
        output, _ = QFileDialog.getSaveFileName(self, "Save new PDF", suggested, "PDF files (*.pdf)")
        if not output:
            return
        self.action = ("new", self.new_size.currentText())
        self.source = None
        self.run_job(
            create_blank_pdf,
            output,
            page_size=self.new_size.currentText(),
            pages=self.new_pages.value(),
        )

    def _success(self, result: object) -> None:
        action, detail = self.action
        if action == "detect" and isinstance(result, list):
            pages = ", ".join(str(n) for n in result) if result else "none"
            self.status.setText(f"Blank page(s): {pages}")
            self.progress.hide()
            return
        super()._success(result)
        output = Path(result) if isinstance(result, Path) else None
        if output is None:
            return
        if action == "blank" and self.source is not None:
            removed = 0
            try:
                import pymupdf
                with pymupdf.open(str(output)) as check:
                    removed = self.source_pages.get("blank", 0) - check.page_count
            except Exception:
                removed = 0
            self.status.setText(f"Saved: {output.name} · removed {removed} blank page(s) · {self.source.name}")
            HistoryStore().add(
                self.source.name,
                "Remove Blank Pages",
                self.source.stat().st_size,
                output.stat().st_size,
                str(output),
            )
        elif action == "resize" and self.source is not None:
            self.status.setText(f"Saved: {output.name} · page size {detail}")
            HistoryStore().add(
                self.source.name,
                "Resize Pages",
                self.source.stat().st_size,
                output.stat().st_size,
                str(output),
            )
        elif action == "new":
            self.status.setText(f"Created: {output.name} · page size {detail}")
            HistoryStore().add(
                output.name,
                "New PDF",
                0,
                output.stat().st_size,
                str(output),
            )
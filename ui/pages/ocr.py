"""OCR PDF and image interface with dependency guidance."""
from pathlib import Path

from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget

from core.jobs.worker import FunctionWorker
from core.ocr.ocr_engine import available_languages, find_tesseract, ocr_image, ocr_pdf


class OcrPage(QWidget):
    def __init__(self) -> None:
        super().__init__(); self.source: Path | None = None; self.executable: Path | None = find_tesseract(); self.worker = None
        layout = QVBoxLayout(self); layout.setContentsMargins(38, 30, 38, 30)
        title = QLabel("OCR"); title.setObjectName("title"); layout.addWidget(title); subtitle = QLabel("Turn scanned PDFs and images into searchable PDFs or text."); subtitle.setObjectName("subtitle"); layout.addWidget(subtitle)
        self.dependency = QLabel(); layout.addWidget(self.dependency); locate = QPushButton("Locate Tesseract"); locate.clicked.connect(self.locate); layout.addWidget(locate)
        row = QHBoxLayout(); self.source_label = QLabel("No file selected"); choose = QPushButton("Choose PDF or Image"); choose.clicked.connect(self.choose); row.addWidget(self.source_label, 1); row.addWidget(choose); layout.addLayout(row)
        form = QFormLayout(); self.language = QComboBox(); form.addRow("Language", self.language); self.output_format = QComboBox(); self.output_format.addItems(["Searchable PDF", "Text File"]); form.addRow("Output", self.output_format); self.dpi = QComboBox(); self.dpi.addItems(["150", "200", "300"]); self.dpi.setCurrentText("200"); form.addRow("DPI", self.dpi); layout.addLayout(form)
        self.progress = QProgressBar(); self.progress.hide(); layout.addWidget(self.progress); self.status = QLabel("OCR runs locally. Documents are never uploaded."); self.status.setObjectName("muted"); layout.addWidget(self.status)
        process = QPushButton("Start OCR"); process.setObjectName("primary"); process.clicked.connect(self.start); layout.addWidget(process); layout.addStretch(); self.refresh_languages()

    def refresh_languages(self) -> None:
        languages = available_languages(self.executable); self.language.clear()
        labels = [("eng", "English (eng)"), ("ind", "Indonesian (ind)")]
        for code, label in labels:
            if code in languages: self.language.addItem(label, code)
        for code in languages:
            if code not in {item[0] for item in labels}: self.language.addItem(code, code)
        self.dependency.setText(f"Tesseract: {self.executable}" if self.executable else "Tesseract: Not Found — install it or locate tesseract.exe")

    def locate(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Locate Tesseract", r"C:\Program Files", "tesseract.exe (tesseract.exe)")
        if name: self.executable = find_tesseract(name); self.refresh_languages()

    def choose(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Choose file", "", "Supported files (*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)")
        if name: self.source = Path(name).resolve(); self.source_label.setText(self.source.name)

    def start(self) -> None:
        if not self.executable: QMessageBox.warning(self, "Tesseract required", "Tesseract OCR was not found. Install it or use Locate Tesseract."); return
        if not self.source: QMessageBox.information(self, "Choose file", "Choose a PDF or image first."); return
        if self.language.count() == 0: QMessageBox.warning(self, "Language data missing", "No Tesseract language data was found."); return
        pdf_output = self.output_format.currentText() == "Searchable PDF"; suffix = ".pdf" if pdf_output else ".txt"
        output, _ = QFileDialog.getSaveFileName(self, "Save OCR output", str(self.source.with_name(f"{self.source.stem}_ocr{suffix}")), f"Output (*{suffix})")
        if not output: return
        language = self.language.currentData(); function = ocr_pdf if self.source.suffix.lower() == ".pdf" else ocr_image
        kwargs = {"language": language, "output_format": "pdf" if pdf_output else "txt", "executable": self.executable}
        if function is ocr_pdf: kwargs["dpi"] = int(self.dpi.currentText())
        self.progress.setValue(0); self.progress.show(); worker = FunctionWorker(function, self.source, output, with_progress=True, **kwargs); self.worker = worker
        worker.signals.progress.connect(lambda value, detail: (self.progress.setValue(value), self.status.setText(detail))); worker.signals.result.connect(self.complete); worker.signals.error.connect(lambda message, details: QMessageBox.critical(self, "OCR failed", message)); worker.signals.finished.connect(lambda: (self.progress.hide(), setattr(self, "worker", None))); QThreadPool.globalInstance().start(worker)

    def complete(self, result: object) -> None:
        output = Path(result); self.status.setText(f"OCR complete: {output.name}"); QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

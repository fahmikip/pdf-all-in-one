"""Image/PDF conversion workspace."""

from __future__ import annotations

from pathlib import Path

from core.jobs.worker import FunctionWorker
from core.office.libreoffice_converter import find_libreoffice, office_to_pdf
from core.office.pdf_to_excel import pdf_to_excel
from core.office.pdf_to_word import pdf_to_word
from core.pdf.converter import IMAGE_EXTENSIONS, images_to_pdf, pdf_to_images
from core.utils.validation import validate_pdf
from PySide6.QtCore import Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class ConversionFileList(QListWidget):
    external_files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            self.external_files_dropped.emit([url.toLocalFile() for url in event.mimeData().urls()])
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class ConverterPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.worker: FunctionWorker | None = None
        self.libreoffice = find_libreoffice()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(38, 30, 38, 30)
        layout.setSpacing(12)
        title = QLabel("Konversi File")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Ubah gambar menjadi PDF atau ekspor halaman PDF sebagai gambar—sepenuhnya offline.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Konversi"))
        self.mode = QComboBox()
        self.mode.addItems(
            [
                "Gambar ke PDF",
                "PDF ke JPG",
                "PDF ke PNG",
                "PDF ke WebP",
                "Word ke PDF",
                "Excel ke PDF",
                "PowerPoint ke PDF",
                "PDF ke Word",
                "PDF ke Excel",
            ]
        )
        self.mode.currentTextChanged.connect(self.mode_changed)
        mode_row.addWidget(self.mode, 1)
        self.locate_office = QPushButton("Temukan LibreOffice")
        self.locate_office.setObjectName("ghost")
        self.locate_office.clicked.connect(self.choose_libreoffice)
        mode_row.addWidget(self.locate_office)
        layout.addLayout(mode_row)
        self.files = ConversionFileList()
        self.files.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.files.setMinimumHeight(210)
        self.files.external_files_dropped.connect(self.add_paths)
        layout.addWidget(self.files)
        file_row = QHBoxLayout()
        add = QPushButton("Tambah File")
        add.setObjectName("ghost")
        add.clicked.connect(self.choose)
        remove = QPushButton("Hapus yang Dipilih")
        remove.setObjectName("ghost")
        remove.clicked.connect(lambda: self.files.takeItem(self.files.currentRow()))
        clear = QPushButton("Bersihkan")
        clear.setObjectName("ghost")
        clear.clicked.connect(self.files.clear)
        file_row.addWidget(add)
        file_row.addWidget(remove)
        file_row.addWidget(clear)
        file_row.addStretch()
        layout.addLayout(file_row)
        settings = QHBoxLayout()
        self.page_size = QComboBox()
        self.page_size.addItems(["A4", "Letter", "Legal", "Fit"])
        settings.addWidget(QLabel("Ukuran halaman"))
        settings.addWidget(self.page_size)
        self.orientation = QComboBox()
        for label, value in (("Otomatis", "auto"), ("Potret", "portrait"), ("Lanskap", "landscape")):
            self.orientation.addItem(label, value)
        settings.addWidget(QLabel("Orientasi"))
        settings.addWidget(self.orientation)
        self.margin = QComboBox()
        for label, value in (("Tanpa", "none"), ("Kecil", "small"), ("Sedang", "medium")):
            self.margin.addItem(label, value)
        self.margin.setCurrentIndex(self.margin.findData("small"))
        settings.addWidget(QLabel("Margin"))
        settings.addWidget(self.margin)
        self.dpi = QComboBox()
        self.dpi.addItems(["72", "96", "150", "200", "300", "600"])
        self.dpi.setCurrentText("150")
        settings.addWidget(QLabel("DPI"))
        settings.addWidget(self.dpi)
        layout.addLayout(settings)
        options = QHBoxLayout()
        options.addWidget(QLabel("Halaman"))
        self.pages = QLineEdit()
        self.pages.setPlaceholderText("Semua halaman, atau mis. 1-3, 5")
        options.addWidget(self.pages, 1)
        options.addWidget(QLabel("Kualitas"))
        self.quality = QSlider(Qt.Orientation.Horizontal)
        self.quality.setRange(1, 100)
        self.quality.setValue(90)
        self.quality.setMaximumWidth(180)
        options.addWidget(self.quality)
        layout.addLayout(options)
        self.progress = QProgressBar()
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = QLabel("Tambahkan file untuk memulai")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)
        process = QPushButton("Konversi")
        process.setObjectName("success")
        process.clicked.connect(self.start)
        layout.addWidget(process)
        layout.addStretch()
        self.mode_changed(self.mode.currentText())

    def mode_changed(self, mode: str) -> None:
        to_pdf = mode == "Gambar ke PDF"
        pdf_image = mode in {"PDF ke JPG", "PDF ke PNG", "PDF ke WebP"}
        office = mode in {"Word ke PDF", "Excel ke PDF", "PowerPoint ke PDF"}
        self.files.clear()
        self.page_size.setEnabled(to_pdf)
        self.orientation.setEnabled(to_pdf)
        self.margin.setEnabled(to_pdf)
        self.dpi.setEnabled(pdf_image)
        self.pages.setEnabled(pdf_image)
        self.quality.setEnabled(pdf_image)
        self.locate_office.setVisible(office)
        if office:
            self.status.setText(f"LibreOffice: {self.libreoffice or 'Tidak Ditemukan'}")
        elif to_pdf:
            self.status.setText("Tambahkan gambar untuk memulai")
        elif mode == "PDF ke Word":
            self.status.setText(
                "Tata letak yang rumit mungkin tidak terkonversi sempurna. Teks, paragraf, dan gambar diutamakan."
            )
        elif mode == "PDF ke Excel":
            self.status.setText("Semua teks dan gambar disusun ke dalam lembar kerja Excel.")
        else:
            self.status.setText("Tambahkan satu PDF untuk memulai")

    def choose_libreoffice(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Temukan LibreOffice", r"C:\Program Files", "soffice.exe (soffice.exe)"
        )
        if name:
            self.libreoffice = find_libreoffice(name)
            self.mode_changed(self.mode.currentText())

    def choose(self) -> None:
        mode = self.mode.currentText()
        if mode == "Gambar ke PDF":
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Pilih gambar", "", "Gambar (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"
            )
        else:
            mode_pdf_extract = mode in {"PDF ke Word", "PDF ke Excel"}
            if mode_pdf_extract:
                path, _ = QFileDialog.getOpenFileName(self, "Pilih file sumber", "", "Berkas PDF (*.pdf)")
                paths = [path] if path else []
            else:
                filters = {
                    "Word ke PDF": "Berkas Word (*.doc *.docx)",
                    "Excel ke PDF": "Berkas Excel (*.xls *.xlsx)",
                    "PowerPoint ke PDF": "Berkas PowerPoint (*.ppt *.pptx)",
                }
                path, _ = QFileDialog.getOpenFileName(
                    self, "Pilih file sumber", "", filters.get(mode, "Berkas PDF (*.pdf)")
                )
                paths = [path] if path else []
            self.files.clear()
        self.add_paths(paths)

    def add_paths(self, paths: list[str]) -> None:
        mode = self.mode.currentText()
        to_pdf = mode == "Gambar ke PDF"
        allowed = {
            "Word ke PDF": {".doc", ".docx"},
            "Excel ke PDF": {".xls", ".xlsx"},
            "PowerPoint ke PDF": {".ppt", ".pptx"},
        }.get(mode, {".pdf"})
        valid = [
            path
            for path in paths
            if Path(path).is_file()
            and (Path(path).suffix.lower() in IMAGE_EXTENSIONS if to_pdf else Path(path).suffix.lower() in allowed)
        ]
        if not to_pdf and valid:
            self.files.clear()
            valid = valid[:1]
        existing = {self.files.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.files.count())}
        for path in valid:
            absolute = str(Path(path).resolve())
            if absolute not in existing:
                self.files.addItem(Path(path).name)
                self.files.item(self.files.count() - 1).setData(Qt.ItemDataRole.UserRole, absolute)
                existing.add(absolute)
        if valid:
            self.status.setText(f"{self.files.count()} file dipilih")
        elif paths:
            self.status.setText("Tidak ada file yang didukung ditambahkan")

    def _paths(self) -> list[str]:
        return [self.files.item(index).data(Qt.ItemDataRole.UserRole) for index in range(self.files.count())]

    def start(self) -> None:
        paths = self._paths()
        if not paths:
            QMessageBox.information(self, "Tambah file", "Tambahkan file sumber terlebih dahulu.")
            return
        mode = self.mode.currentText()
        if mode == "Gambar ke PDF":
            output, _ = QFileDialog.getSaveFileName(
                self, "Simpan PDF", str(Path(paths[0]).with_name("images.pdf")), "Berkas PDF (*.pdf)"
            )
            if not output:
                return
            function, args, kwargs = (
                images_to_pdf,
                (paths, output),
                {
                    "page_size": self.page_size.currentText().lower(),
                    "orientation": self.orientation.currentData(),
                    "margin": self.margin.currentData(),
                },
            )
        elif mode in {"PDF ke JPG", "PDF ke PNG", "PDF ke WebP"}:
            try:
                validate_pdf(paths[0])
            except Exception as exc:
                QMessageBox.warning(self, "Tidak Dapat Membuka PDF", str(exc))
                return
            folder = QFileDialog.getExistingDirectory(self, "Pilih folder output", str(Path(paths[0]).parent))
            if not folder:
                return
            function, args = pdf_to_images, (paths[0], folder)
            kwargs = {
                "image_format": mode.rsplit(" ", 1)[-1].lower(),
                "dpi": int(self.dpi.currentText()),
                "quality": self.quality.value(),
                "page_range": self.pages.text(),
            }
        elif mode in {"Word ke PDF", "Excel ke PDF", "PowerPoint ke PDF"}:
            if not self.libreoffice:
                QMessageBox.warning(
                    self,
                    "LibreOffice diperlukan",
                    "LibreOffice wajib untuk konversi Office. Pasang aplikasinya atau klik Temukan LibreOffice.",
                )
                return
            output, _ = QFileDialog.getSaveFileName(
                self, "Simpan PDF", str(Path(paths[0]).with_suffix(".pdf")), "Berkas PDF (*.pdf)"
            )
            if not output:
                return
            function, args, kwargs = office_to_pdf, (paths[0], output), {"executable": self.libreoffice}
        elif mode == "PDF ke Excel":
            try:
                validate_pdf(paths[0])
            except Exception as exc:
                QMessageBox.warning(self, "Tidak Dapat Membuka PDF", str(exc))
                return
            output, _ = QFileDialog.getSaveFileName(
                self, "Simpan buku kerja Excel", str(Path(paths[0]).with_suffix(".xlsx")), "Berkas Excel (*.xlsx)"
            )
            if not output:
                return
            function, args, kwargs = pdf_to_excel, (paths[0], output), {}
        else:
            output, _ = QFileDialog.getSaveFileName(
                self, "Simpan dokumen Word", str(Path(paths[0]).with_suffix(".docx")), "Berkas Word (*.docx)"
            )
            if not output:
                return
            function, args, kwargs = pdf_to_word, (paths[0], output), {}
        self.progress.setValue(0)
        self.progress.show()
        self.status.setText("Mengonversi…")
        worker = FunctionWorker(function, *args, with_progress=True, **kwargs)
        self.worker = worker
        worker.signals.progress.connect(
            lambda value, detail: (self.progress.setValue(value), self.status.setText(detail))
        )
        worker.signals.result.connect(self.completed)
        worker.signals.error.connect(self.failed)
        worker.signals.finished.connect(lambda: (self.progress.hide(), setattr(self, "worker", None)))
        QThreadPool.globalInstance().start(worker)

    def completed(self, result: object) -> None:
        path = Path(result[0]).parent if isinstance(result, list) else Path(result)
        self.status.setText("Konversi selesai")
        answer = QMessageBox.question(
            self,
            "Konversi selesai",
            "Output tersimpan. Buka foldernya?",
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Close,
        )
        if answer == QMessageBox.StandardButton.Open:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path if path.is_dir() else path.parent)))

    def failed(self, message: str, details: str) -> None:
        dialog = QMessageBox(QMessageBox.Icon.Critical, "Konversi gagal", message, parent=self)
        dialog.setDetailedText(details)
        dialog.exec()

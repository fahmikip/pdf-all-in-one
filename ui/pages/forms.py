"""Fill PDF form fields and add visual signatures."""

from __future__ import annotations

from pathlib import Path

import pymupdf
from core.jobs.worker import FunctionWorker
from core.pdf.forms import fill_pdf_form, list_form_fields, sign_pdf
from core.utils.history import HistoryStore
from core.utils.validation import validate_pdf
from PySide6.QtCore import QThreadPool, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.signature_pad import SignaturePad

SIGN_WIDTH = 200.0
SIGN_HEIGHT = 70.0


class FormsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.worker: FunctionWorker | None = None
        self.pool = QThreadPool.globalInstance()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(38, 30, 38, 30)
        layout.setSpacing(14)
        title = QLabel("Formulir & Tanda Tangan PDF")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel(
            "Isi bidang formulir PDF interaktif atau beri stempel tanda tangan visual—sepenuhnya offline."
        )
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)
        tabs.addTab(self._fill_tab(), "Isi Formulir")
        tabs.addTab(self._sign_tab(), "Tanda Tangani Dokumen")
        self.status = QLabel("Pilih PDF untuk memulai")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)

    def _choose_source_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.source_label = QLabel("Belum ada PDF dipilih")
        choose = QPushButton("Pilih PDF")
        choose.setObjectName("ghost")
        choose.clicked.connect(self.choose)
        row.addWidget(self.source_label, 1)
        row.addWidget(choose)
        return row

    def _fill_tab(self) -> QWidget:
        tab = QWidget()
        box = QVBoxLayout(tab)
        box.addLayout(self._choose_source_row())
        self.fields = QTableWidget(0, 5)
        self.fields.setHorizontalHeaderLabels(["Halaman", "Nama Bidang", "Tipe", "Nilai Saat Ini", "Nilai Baru"])
        self.fields.horizontalHeader().setStretchLastSection(True)
        self.fields.verticalHeader().setVisible(False)
        box.addWidget(self.fields, 1)
        actions = QHBoxLayout()
        self.fill_progress = QProgressBar()
        self.fill_progress.hide()
        actions.addWidget(self.fill_progress, 1)
        save = QPushButton("Simpan PDF Terisi")
        save.setObjectName("success")
        save.clicked.connect(self.save_filled)
        actions.addWidget(save)
        box.addLayout(actions)
        hint = QLabel("Isi nilai pada kolom Nilai Baru, lalu simpan salinan. File asli tidak pernah diubah.")
        hint.setObjectName("muted")
        box.addWidget(hint)
        return tab

    def _sign_tab(self) -> QWidget:
        tab = QWidget()
        box = QVBoxLayout(tab)
        box.addLayout(self._choose_source_row())
        image_row = QHBoxLayout()
        self.image_label = QLabel("Belum ada gambar tanda tangan dipilih")
        choose = QPushButton("Pilih Gambar Tanda Tangan")
        choose.setObjectName("ghost")
        choose.clicked.connect(self.choose_image)
        image_row.addWidget(self.image_label, 1)
        image_row.addWidget(choose)
        box.addLayout(image_row)
        self.draw_toggle = QCheckBox("Gambar tanda tangan dengan mouse / sentuhan")
        self.draw_toggle.setToolTip("Buat sketsa tanda tangan Anda pada papan di bawah, bukan memakai gambar.")
        self.draw_toggle.toggled.connect(self.toggle_draw)
        box.addWidget(self.draw_toggle)
        pad_row = QHBoxLayout()
        self.pad = SignaturePad()
        pad_row.addWidget(self.pad, 1)
        clear_pad = QPushButton("Bersihkan")
        clear_pad.setObjectName("ghost")
        clear_pad.clicked.connect(self.pad.clear)
        pad_row.addWidget(clear_pad)
        self.pad_row = pad_row
        clear_pad.setVisible(False)
        self.pad.setVisible(False)
        box.addLayout(pad_row)
        controls = QHBoxLayout()
        self.page = QSpinBox()
        self.page.setRange(1, 999)
        self.page.setValue(1)
        controls.addWidget(QLabel("Halaman"))
        controls.addWidget(self.page)
        self.position = QComboBox()
        for label, value in (
            ("Kiri bawah", "Bottom-left"),
            ("Kanan bawah", "Bottom-right"),
            ("Kiri atas", "Top-left"),
            ("Kanan atas", "Top-right"),
        ):
            self.position.addItem(label, value)
        controls.addWidget(QLabel("Posisi"))
        controls.addWidget(self.position)
        controls.addStretch()
        box.addLayout(controls)
        fields = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Nama penanda tangan (opsional)")
        self.role = QLineEdit()
        self.role.setPlaceholderText("Peran, mis. Manajer (opsional)")
        fields.addWidget(self.name, 1)
        fields.addWidget(self.role, 1)
        box.addLayout(fields)
        actions = QHBoxLayout()
        self.sign_progress = QProgressBar()
        self.sign_progress.hide()
        actions.addWidget(self.sign_progress, 1)
        sign = QPushButton("Tanda Tangani PDF")
        sign.setObjectName("primary")
        sign.clicked.connect(self.save_signed)
        actions.addWidget(sign)
        box.addLayout(actions)
        hint = QLabel("Penandatangan menambah stempel tanda tangan visual; tidak membuat tanda tangan kriptografis.")
        hint.setObjectName("muted")
        box.addWidget(hint)
        return tab

    def choose(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Pilih PDF", "", "Berkas PDF (*.pdf)")
        if not name:
            return
        try:
            info = validate_pdf(name)
        except Exception as exc:
            QMessageBox.warning(self, "Tidak Dapat Membuka PDF", str(exc))
            return
        self.source = info.path
        self.source_label.setText(f"{info.path.name} · {info.pages} halaman")
        with pymupdf.open(self.source) as doc:
            self.page_size = (doc[0].rect.width, doc[0].rect.height) if doc.page_count else (595.0, 842.0)
        self.page.setMaximum(info.pages)
        self.load_fields()

    def load_fields(self) -> None:
        if not self.source:
            return
        try:
            fields = list_form_fields(self.source)
        except Exception as exc:
            QMessageBox.warning(self, "Tidak ada bidang formulir", str(exc))
            return
        self.fields.setRowCount(len(fields))
        for row, field in enumerate(fields):
            self.fields.setItem(row, 0, QTableWidgetItem(str(field["page"])))
            self.fields.setItem(row, 1, QTableWidgetItem(str(field["name"])))
            self.fields.setItem(row, 2, QTableWidgetItem(str(field["type"])))
            self.fields.setItem(row, 3, QTableWidgetItem(str(field["value"])))
            self.fields.setItem(row, 4, QTableWidgetItem(""))
        self.fields.resizeColumnsToContents()
        self.status.setText(f"Ditemukan {len(fields)} bidang formulir")

    def choose_image(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Pilih gambar tanda tangan", "", "Gambar (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if not name:
            return
        self.image = Path(name)
        self.image_label.setText(self.image.name)

    def toggle_draw(self, checked: bool) -> None:
        self.pad.setVisible(checked)
        self.pad_row.itemAt(1).widget().setVisible(checked)
        chosen = getattr(self, "image", None)
        self.image_label.setText(
            "Gambar tanda tangan Anda pada papan di bawah"
            if checked
            else (chosen.name if chosen else "Belum ada gambar tanda tangan dipilih")
        )

    def _signature_source(self) -> Path | None:
        if self.draw_toggle.isChecked():
            if self.pad.is_empty():
                QMessageBox.information(self, "Tanda tangani papan", "Gambar tanda tangan Anda terlebih dahulu.")
                return None
            return self.pad.png_path()
        return getattr(self, "image", None)

    def _updates(self) -> dict[str, object]:
        updates: dict[str, object] = {}
        for row in range(self.fields.rowCount()):
            name = self.fields.item(row, 1).text().strip()
            value_item = self.fields.item(row, 4)
            if not name:
                continue
            value = value_item.text().strip() if value_item else ""
            if not value:
                continue
            if self.fields.item(row, 2).text() == "CheckBox":
                updates[name] = value.lower() in ("1", "x", "yes", "on", "true")
            else:
                updates[name] = value
        return updates

    def save_filled(self) -> None:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        updates = self._updates()
        if not updates:
            QMessageBox.information(self, "Masukkan nilai", "Isi Nilai Baru untuk setidaknya satu bidang.")
            return
        output, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan PDF terisi",
            str(self.source.with_name(f"{self.source.stem}_filled.pdf")),
            "Berkas PDF (*.pdf)",
        )
        if not output:
            return
        self.target = Path(output)
        self._run_job("fill", fill_pdf_form, updates)

    def save_signed(self) -> None:
        if not self.source:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        image = self._signature_source()
        if image is None and not self.name.text() and not self.role.text():
            QMessageBox.information(
                self, "Tanda tangan diperlukan", "Pilih atau gambar tanda tangan, atau isi nama penanda tangan."
            )
            return
        output, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan PDF yang ditandatangani",
            str(self.source.with_name(f"{self.source.stem}_signed.pdf")),
            "Berkas PDF (*.pdf)",
        )
        if not output:
            return
        self.target = Path(output)
        width, height = getattr(self, "page_size", (595.0, 842.0))
        margin = 40.0
        bottom_y = height - margin
        right_x = width - margin
        left_x, top_y = margin, height - margin - SIGN_HEIGHT
        positions = {
            "Bottom-left": (left_x, top_y, left_x + SIGN_WIDTH, top_y + SIGN_HEIGHT),
            "Bottom-right": (right_x - SIGN_WIDTH, bottom_y - SIGN_HEIGHT, right_x, bottom_y),
            "Top-left": (margin, margin, margin + SIGN_WIDTH, margin + SIGN_HEIGHT),
            "Top-right": (right_x - SIGN_WIDTH, margin, right_x, margin + SIGN_HEIGHT),
        }
        rect = positions[self.position.currentData()]
        self._run_job(
            "sign",
            sign_pdf,
            image_path=image,
            page_number=self.page.value(),
            rect=rect,
            name=self.name.text().strip(),
            role=self.role.text().strip(),
        )

    def _run_job(self, action: str, function, *args, **kwargs) -> None:
        progress = self.fill_progress if action == "fill" else self.sign_progress
        self.status.setText("Memproses…")
        progress.setValue(0)
        progress.show()
        worker = FunctionWorker(function, self.source, self.target, *args, with_progress=True, **kwargs)
        self.worker = worker
        worker.signals.progress.connect(lambda value, detail: (progress.setValue(value), self.status.setText(detail)))
        worker.signals.result.connect(lambda result: self.completed(action, result))
        worker.signals.error.connect(lambda message, details: self.failed(message, details))
        worker.signals.finished.connect(lambda: (progress.hide(), setattr(self, "worker", None)))
        self.pool.start(worker)

    def completed(self, action: str, result: object) -> None:
        output = Path(result)
        self.status.setText(f"Tersimpan: {output.name}")
        HistoryStore().add(
            self.source.name,
            "Isi Formulir" if action == "fill" else "Tanda Tangani PDF",
            self.source.stat().st_size,
            0,
            str(output),
        )
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output.parent)))

    def failed(self, message: str, details: str) -> None:
        self.status.setText("Operasi gagal")
        dialog = QMessageBox(QMessageBox.Icon.Critical, "Terjadi kesalahan", message, parent=self)
        dialog.setDetailedText(details)
        dialog.exec()

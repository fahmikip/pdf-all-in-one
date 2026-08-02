"""Visual, non-destructive PDF page organizer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QImage, QPixmap, QTransform
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from core.jobs.worker import FunctionWorker
from core.pdf.page_manager import PageSpec, organize_pages
from core.utils.validation import validate_pdf
from ui.widgets.drop_zone import DropZone


@dataclass(frozen=True, slots=True)
class OrganizerState:
    pages: tuple[PageSpec, ...]


def render_thumbnails(path: str | Path, progress=None) -> list[QImage]:
    images: list[QImage] = []
    with fitz.open(path) as document:
        total = document.page_count
        matrix = fitz.Matrix(0.24, 0.24)
        for index, page in enumerate(document):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False, colorspace=fitz.csRGB)
            image = QImage(pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, QImage.Format.Format_RGB888).copy()
            images.append(image)
            if progress:
                progress(round((index + 1) / total * 100), f"Rendering page {index + 1} of {total}")
    return images


class OrganizerPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.thumbnails: list[QImage] = []
        self.undo_stack: list[OrganizerState] = []
        self.redo_stack: list[OrganizerState] = []
        self._loading_worker: FunctionWorker | None = None
        layout = QVBoxLayout(self); layout.setContentsMargins(32, 25, 32, 25); layout.setSpacing(11)
        title = QLabel("Organize PDF"); title.setObjectName("title"); layout.addWidget(title)
        subtitle = QLabel("Drag pages to reorder. Use Ctrl or Shift to select multiple pages."); subtitle.setObjectName("subtitle"); layout.addWidget(subtitle)
        self.drop = DropZone(); self.drop.setMaximumHeight(155); self.drop.choose_requested.connect(self.choose); self.drop.files_dropped.connect(self.open_files); layout.addWidget(self.drop)
        self.progress = QProgressBar(); self.progress.hide(); layout.addWidget(self.progress)
        self.status = QLabel("Choose a PDF to begin"); self.status.setObjectName("muted"); layout.addWidget(self.status)
        self.grid = QListWidget(); self.grid.setViewMode(QListWidget.ViewMode.IconMode); self.grid.setIconSize(QSize(110, 145)); self.grid.setGridSize(QSize(145, 190)); self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setMovement(QListWidget.Movement.Snap); self.grid.setDragDropMode(QListWidget.DragDropMode.InternalMove); self.grid.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection); self.grid.setSpacing(8); layout.addWidget(self.grid, 1)
        self.grid.model().rowsAboutToBeMoved.connect(lambda *args: self._checkpoint())
        self.grid.model().rowsMoved.connect(lambda *args: self._renumber())
        toolbar = QHBoxLayout()
        actions = (("Undo", self.undo), ("Redo", self.redo), ("Reset", self.reset), ("Remove", self.remove_selected), ("Duplicate", self.duplicate_selected), ("↶ 90°", lambda: self.rotate_selected(-90)), ("↷ 90°", lambda: self.rotate_selected(90)), ("Extract", self.extract_selected))
        for label, callback in actions:
            button = QPushButton(label); button.clicked.connect(callback); toolbar.addWidget(button)
        toolbar.addStretch(); save = QPushButton("Save Organized PDF"); save.setObjectName("primary"); save.clicked.connect(self.save); toolbar.addWidget(save); layout.addLayout(toolbar)

    def choose(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Choose PDF", "", "PDF files (*.pdf)")
        if filename: self.open_files([filename])

    def open_files(self, files: list[str]) -> None:
        try: info = validate_pdf(files[0])
        except Exception as exc: QMessageBox.warning(self, "Cannot open PDF", str(exc)); return
        self.source = info.path; self.grid.clear(); self.thumbnails.clear(); self.undo_stack.clear(); self.redo_stack.clear()
        self.progress.setValue(0); self.progress.show(); self.status.setText(f"Loading {info.path.name} · {info.pages} pages")
        worker = FunctionWorker(render_thumbnails, info.path, with_progress=True); self._loading_worker = worker
        worker.signals.progress.connect(lambda value, text: (self.progress.setValue(value), self.status.setText(text)))
        worker.signals.result.connect(self._thumbnails_ready); worker.signals.error.connect(lambda message, details: QMessageBox.critical(self, "Preview failed", message))
        worker.signals.finished.connect(lambda: self.progress.hide()); worker.signals.finished.connect(lambda: setattr(self, "_loading_worker", None))
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(worker)

    def _thumbnails_ready(self, images: object) -> None:
        self.thumbnails = list(images)  # type: ignore[arg-type]
        self._restore(OrganizerState(tuple(PageSpec(index) for index in range(len(self.thumbnails)))))
        self.undo_stack.clear(); self.redo_stack.clear(); self.status.setText(f"Ready · {len(self.thumbnails)} pages")

    def _state(self) -> OrganizerState:
        pages = []
        for index in range(self.grid.count()):
            raw = self.grid.item(index).data(Qt.ItemDataRole.UserRole)
            pages.append(PageSpec(int(raw[0]), int(raw[1])))
        return OrganizerState(tuple(pages))

    def _restore(self, state: OrganizerState) -> None:
        self.grid.clear()
        for position, spec in enumerate(state.pages, start=1):
            pixmap = QPixmap.fromImage(self.thumbnails[spec.source_index])
            if spec.rotation: pixmap = pixmap.transformed(QTransform().rotate(spec.rotation), Qt.TransformationMode.SmoothTransformation)
            item = QListWidgetItem(QIcon(pixmap), f"Page {position}")
            item.setData(Qt.ItemDataRole.UserRole, (spec.source_index, spec.rotation)); item.setToolTip(f"Source page {spec.source_index + 1} · Rotation {spec.rotation % 360}°"); self.grid.addItem(item)

    def _checkpoint(self) -> None:
        self.undo_stack.append(self._state()); self.redo_stack.clear()

    def undo(self) -> None:
        if self.undo_stack:
            self.redo_stack.append(self._state()); self._restore(self.undo_stack.pop())

    def redo(self) -> None:
        if self.redo_stack:
            self.undo_stack.append(self._state()); self._restore(self.redo_stack.pop())

    def reset(self) -> None:
        if self.thumbnails:
            self._checkpoint(); self._restore(OrganizerState(tuple(PageSpec(i) for i in range(len(self.thumbnails)))))

    def selected_rows(self) -> list[int]:
        return sorted((self.grid.row(item) for item in self.grid.selectedItems()))

    def remove_selected(self) -> None:
        rows = self.selected_rows()
        if not rows: return
        if len(rows) == self.grid.count(): QMessageBox.information(self, "Cannot remove pages", "A PDF must contain at least one page."); return
        self._checkpoint()
        for row in reversed(rows): self.grid.takeItem(row)
        self._renumber()

    def duplicate_selected(self) -> None:
        rows = self.selected_rows()
        if not rows: return
        self._checkpoint()
        specs = self._state().pages
        offset = 0
        for row in rows:
            spec = specs[row]; self._insert_spec(row + 1 + offset, spec); offset += 1
        self._renumber()

    def _insert_spec(self, row: int, spec: PageSpec) -> None:
        pixmap = QPixmap.fromImage(self.thumbnails[spec.source_index])
        if spec.rotation: pixmap = pixmap.transformed(QTransform().rotate(spec.rotation), Qt.TransformationMode.SmoothTransformation)
        item = QListWidgetItem(QIcon(pixmap), "")
        item.setData(Qt.ItemDataRole.UserRole, (spec.source_index, spec.rotation)); self.grid.insertItem(row, item)

    def rotate_selected(self, degrees: int) -> None:
        if not self.grid.selectedItems(): return
        self._checkpoint()
        for item in self.grid.selectedItems():
            source, rotation = item.data(Qt.ItemDataRole.UserRole); item.setData(Qt.ItemDataRole.UserRole, (source, (rotation + degrees) % 360))
        self._restore(self._state())

    def _renumber(self) -> None:
        for index in range(self.grid.count()): self.grid.item(index).setText(f"Page {index + 1}")

    def extract_selected(self) -> None:
        if not self.source or not self.selected_rows(): return
        pages = [self._state().pages[row] for row in self.selected_rows()]
        output, _ = QFileDialog.getSaveFileName(self, "Save extracted pages", str(self.source.with_name(f"{self.source.stem}_extracted.pdf")), "PDF files (*.pdf)")
        if output:
            try: organize_pages(self.source, output, pages); QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(output).parent)))
            except Exception as exc: QMessageBox.critical(self, "Extraction failed", str(exc))

    def save(self) -> None:
        if not self.source: QMessageBox.information(self, "Select a PDF", "Choose a PDF first."); return
        output, _ = QFileDialog.getSaveFileName(self, "Save organized PDF", str(self.source.with_name(f"{self.source.stem}_organized.pdf")), "PDF files (*.pdf)")
        if not output: return
        self.progress.setRange(0, 0); self.progress.show(); self.status.setText("Saving organized PDF…")
        worker = FunctionWorker(organize_pages, self.source, output, self._state().pages); self._loading_worker = worker
        worker.signals.result.connect(lambda result: (self.status.setText("Organized PDF saved successfully"), QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(result).parent)))))
        worker.signals.error.connect(lambda message, details: QMessageBox.critical(self, "Save failed", message)); worker.signals.finished.connect(lambda: (self.progress.setRange(0, 100), self.progress.hide(), setattr(self, "_loading_worker", None)))
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(worker)

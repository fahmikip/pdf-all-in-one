"""Interactive page editor: drag images, resize, and add styled text."""
from __future__ import annotations

from pathlib import Path

import fitz
from PySide6.QtCore import Qt, QThreadPool, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QFontMetricsF, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.jobs.worker import FunctionWorker
from core.pdf.watermark import insert_objects
from core.utils.validation import validate_pdf

MOVE = QGraphicsItem.GraphicsItemFlag.ItemIsMovable
SELECTABLE = QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
GEOMETRY = QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
SELECT_CHANGE = QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged

HANDLE_COLOR = QColor("#2563eb")
HANDLE_SIZE = 10.0
MIN_SIZE = 20.0


def _pt_color(color: QColor) -> list[int]:
    return [color.red(), color.green(), color.blue()]


class HandleItem(QGraphicsRectItem):
    def __init__(self, owner: "ObjectItem", anchor: str) -> None:
        super().__init__(-HANDLE_SIZE / 2, -HANDLE_SIZE / 2, HANDLE_SIZE, HANDLE_SIZE)
        self.owner = owner
        self.anchor = anchor
        self.setBrush(HANDLE_COLOR)
        self.setPen(QPen(Qt.GlobalColor.white, 1))
        self.setCursor(Qt.CursorShape.SizeFDiagCursor if anchor in ("tl", "br") else Qt.CursorShape.SizeBDiagCursor)
        self.setZValue(50)

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        self.owner.resize_from_handle(self.anchor, self.mapToParent(event.pos()))
        event.accept()


class ObjectItem(QGraphicsRectItem):
    def __init__(self, x: float, y: float, width: float, height: float) -> None:
        super().__init__(0, 0, width, height)
        self.setPos(x, y)
        self.setFlag(MOVE, True)
        self.setFlag(SELECTABLE, True)
        self.setFlag(GEOMETRY, True)
        self.setZValue(10)
        self._handles: dict[str, HandleItem] = {}
        self._resizable = True
        self._build_handles()

    def _build_handles(self) -> None:
        rect = self.rect()
        for anchor, point in (("tl", (0.0, 0.0)), ("tr", (rect.width(), 0.0)), ("br", (rect.width(), rect.height())), ("bl", (0.0, rect.height()))):
            handle = HandleItem(self, anchor)
            handle.setParentItem(self)
            handle.setPos(*point)
            self._handles[anchor] = handle
        self._set_handles(False)

    def _set_handles(self, visible: bool) -> None:
        if self._resizable:
            for handle in self._handles.values():
                handle.setVisible(visible)

    def itemChange(self, change, value):
        if change == SELECT_CHANGE:
            self._set_handles(bool(value))
        return super().itemChange(change, value)

    def resize_from_handle(self, anchor: str, point: QPointF) -> None:
        rect = self.rect()
        width = rect.width(); height = rect.height()
        if anchor in ("br", "tr"):
            new_width = max(MIN_SIZE, point.x())
            new_height = height * (new_width / width)
        else:
            new_width = width * (point.y() / height) if point.y() > 0 else MIN_SIZE
            new_width = max(MIN_SIZE, new_width)
            new_height = height * (new_width / width)
        self._apply_size(new_width, new_height)

    def _apply_size(self, width: float, height: float) -> None:
        self.setRect(0, 0, width, height)
        rect = self.rect()
        positions = {"tl": (0.0, 0.0), "tr": (rect.width(), 0.0), "br": (rect.width(), rect.height()), "bl": (0.0, rect.height())}
        for anchor, point in positions.items():
            self._handles[anchor].setPos(*point)
        self.update()


class ImageItem(ObjectItem):
    def __init__(self, x: float, y: float, width: float, height: float, path: str, pixmap: QPixmap) -> None:
        super().__init__(x, y, width, height)
        self.path = path
        self.pixmap = pixmap
        self.setPen(QPen(HANDLE_COLOR, 1.5, Qt.PenStyle.DashLine))

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.drawPixmap(self.rect(), self.pixmap)
        if self.isSelected():
            painter.setPen(QPen(HANDLE_COLOR, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect())


class TextItem(ObjectItem):
    def __init__(self, x: float, y: float, text: str, family: str, size_pt: float, color: QColor, zoom: float) -> None:
        super().__init__(x, y, 1, 1)
        self.text = text
        self.size_pt = size_pt
        self.zoom = zoom
        self.color = QColor(color)
        self._resizable = False
        self._set_handles(False)
        self._font = QFont(family)
        self._font.setPointSizeF(size_pt * zoom * 0.75)
        self._update_glyphs()

    def _update_glyphs(self) -> None:
        metrics = QFontMetricsF(self._font)
        bounds = metrics.boundingRect(self.text)
        self.setRect(4, 4, max(bounds.width() + 8, 20), max(bounds.height() + 8, 14))

    def mouseDoubleClickEvent(self, event) -> None:
        new_text, ok = QInputDialog.getText(None, "Edit text", "Text:", text=self.text)
        if ok:
            self.text = new_text
            self._update_glyphs()
            self.update()
        event.accept()

    def apply_style(self, family: str, size_pt: float, color: QColor) -> None:
        self.text = self.text
        self.size_pt = size_pt
        self.color = QColor(color)
        self._font = QFont(family)
        self._font.setPointSizeF(size_pt * self.zoom * 0.75)
        self._update_glyphs()
        self.update()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setFont(self._font)
        painter.setPen(self.color)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text)
        if self.isSelected():
            painter.setPen(QPen(HANDLE_COLOR, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect())


class EditorPage(QWidget):
    IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp)"

    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.zoom = 1.0
        self.page_objects: dict[int, list] = {}
        self._page_index = 0
        self._pages: dict[int, QPixmap] = {}
        self._background: QGraphicsPixmapItem | None = None
        self._block = False
        self._text_color = QColor("#111827")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        choose = QPushButton("Choose PDF"); choose.clicked.connect(self._choose_pdf); top.addWidget(choose)
        self.source_label = QLabel("No PDF selected"); self.source_label.setObjectName("muted"); top.addWidget(self.source_label, 1)
        top.addWidget(QLabel("Page"))
        self.page_spin = QSpinBox(); self.page_spin.setRange(1, 1); self.page_spin.setEnabled(False); self.page_spin.valueChanged.connect(self._switch_page); top.addWidget(self.page_spin)
        self.save_btn = QPushButton("Save PDF"); self.save_btn.setObjectName("primary"); self.save_btn.setEnabled(False); self.save_btn.clicked.connect(self._save); top.addWidget(self.save_btn)
        root.addLayout(top)

        middle = QHBoxLayout()
        controls = QVBoxLayout()
        actions = QHBoxLayout()
        add_image = QPushButton("Add Image"); add_image.clicked.connect(self._add_image); actions.addWidget(add_image)
        add_text = QPushButton("Add Text"); add_text.clicked.connect(self._add_text); actions.addWidget(add_text)
        delete = QPushButton("Delete"); delete.clicked.connect(self._delete_selected); actions.addWidget(delete)
        controls.addLayout(actions)

        self.text_group = QWidget(); text_form = QFormLayout(self.text_group); text_form.setContentsMargins(0, 8, 0, 0)
        self.font_combo = QFontComboBox(); self.font_combo.currentFontChanged.connect(self._apply_text_style); text_form.addRow("Font", self.font_combo)
        self.size_spin = QSpinBox(); self.size_spin.setRange(6, 300); self.size_spin.setValue(16); self.size_spin.valueChanged.connect(self._apply_text_style); text_form.addRow("Size (pt)", self.size_spin)
        self.color_btn = QPushButton("Black"); self.color_btn.clicked.connect(self._pick_color); self._refresh_color_btn(); text_form.addRow("Color", self.color_btn)
        controls.addWidget(self.text_group)

        self.image_group = QWidget(); image_form = QFormLayout(self.image_group); image_form.setContentsMargins(0, 8, 0, 0)
        self.width_spin = QSpinBox(); self.width_spin.setRange(5, 100); self.width_spin.setSuffix(" % of page"); self.width_spin.setValue(50); self.width_spin.valueChanged.connect(self._apply_image_width); image_form.addRow("Size", self.width_spin)
        controls.addWidget(self.image_group)
        controls.addStretch(1)
        middle.addLayout(controls)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setBackgroundBrush(QColor("#1f2430"))
        self.scene.selectionChanged.connect(self._sync_controls)
        middle.addWidget(self.view, 1)
        root.addLayout(middle, 1)

        self.status = QLabel("Choose a PDF, then add photos and text. Drag to position, resize via corner handles.")
        self.status.setObjectName("muted"); root.addWidget(self.status)
        self._sync_groups()

    def _refresh_color_btn(self) -> None:
        self.color_btn.setStyleSheet(f"background-color: {self._text_color.name()}; color: {'white' if self._text_color.lightness() < 128 else 'black'}; border-radius: 4px;")

    def _choose_pdf(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Choose PDF", "", "PDF files (*.pdf)")
        if not name: return
        try:
            info = validate_pdf(name)
            with fitz.open(info.path) as document:
                width = document[0].rect.width
        except Exception as exc:
            QMessageBox.warning(self, "Cannot open PDF", str(exc)); return
        self.source = info.path
        self.zoom = max(1.0, min(2.5, 860 / width))
        self._pages = {}; self.page_objects = {}; self._background = None
        self.scene.clear()
        self.source_label.setText(self.source.name)
        self.page_spin.blockSignals(True)
        self.page_spin.setRange(1, info.pages); self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.page_spin.setEnabled(True); self.save_btn.setEnabled(True)
        self._page_index = 0
        self._load_page(0)
        self.status.setText(f"{info.pages} page(s) loaded. Drag objects; resize with corner dots; save to a new PDF.")

    def _render_page(self, index: int) -> QPixmap:
        if index in self._pages: return self._pages[index]
        with fitz.open(self.source) as document:
            pixmap = document[index].get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom), alpha=False)
        image = QImage(pixmap.samples, pixmap.width, pixmap.height, pixmap.stride, QImage.Format.Format_RGB888).copy()
        result = QPixmap.fromImage(image)
        self._pages[index] = result
        return result

    def _page_geometry(self) -> QPixmap:
        pixmap = self._render_page(self._page_index)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        return pixmap

    def _load_page(self, index: int) -> None:
        pixmap = self._page_geometry()
        self._background = QGraphicsPixmapItem(pixmap)
        self._background.setZValue(-1)
        self.scene.addItem(self._background)
        for item in self.page_objects.get(index, []):
            if item.scene() is None:
                self.scene.addItem(item)

    def _switch_page(self, index: int) -> None:
        if self.source is None: return
        if index - 1 == self._page_index: return
        if self._page_index in self.page_objects:
            for item in self.page_objects[self._page_index]:
                self.scene.removeItem(item)
        self.scene.clear()
        self._page_index = index - 1
        self._load_page(self._page_index)

    def _add_image(self) -> None:
        if self.source is None: QMessageBox.information(self, "Choose PDF", "Choose a PDF first."); return
        name, _ = QFileDialog.getOpenFileName(self, "Choose photo or image", "", self.IMAGE_FILTER)
        if not name: return
        pixmap = QPixmap(name)
        if pixmap.isNull():
            QMessageBox.warning(self, "Cannot open image", "That image file could not be read."); return
        page_pixmap = self._render_page(self._page_index)
        width = page_pixmap.width() * .5; height = width * pixmap.height() / pixmap.width()
        x = (page_pixmap.width() - width) / 2; y = (page_pixmap.height() - height) / 2
        path = str(Path(name).resolve())
        item = ImageItem(x, y, width, height, path, pixmap)
        self.scene.addItem(item); item.setSelected(True)
        self.status.setText("Image added. Drag to position; use corner dots to resize.")
        self._sync_controls()

    def _add_text(self) -> None:
        if self.source is None: QMessageBox.information(self, "Choose PDF", "Choose a PDF first."); return
        page_pixmap = self._render_page(self._page_index)
        item = TextItem(page_pixmap.width() / 2 - 60, page_pixmap.height() / 2 - 20, "Teks baru", self.font_combo.currentFont().family(), self.size_spin.value(), self._text_color, self.zoom)
        self.scene.addItem(item); item.setSelected(True)
        self.status.setText("Text added. Double-click the text to edit it.")

    def _delete_selected(self) -> None:
        for item in list(self.scene.selectedItems()):
            if isinstance(item, (ImageItem, TextItem)):
                self.scene.removeItem(item)

    def _delete_selected(self) -> None:
        for item in list(self.scene.selectedItems()):
            if isinstance(item, (ImageItem, TextItem)):
                self.scene.removeItem(item); item.deleteLater()

    def _selected_object(self):
        for item in self.scene.selectedItems():
            if isinstance(item, (ImageItem, TextItem)):
                return item
        return None

    def _apply_text_style(self, *_) -> None:
        if self._block: return
        item = self._selected_object()
        if not isinstance(item, TextItem): return
        item.apply_style(self.font_combo.currentFont().family(), self.size_spin.value(), self._text_color)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(self._text_color, self, "Text color")
        if not color.isValid(): return
        self._text_color = color
        self._refresh_color_btn()
        self._apply_text_style()

    def _apply_image_width(self, value: int) -> None:
        if self._block or self._background is None: return
        item = self._selected_object()
        if not isinstance(item, ImageItem): return
        page_width = self._background.pixmap().width()
        new_width = max(MIN_SIZE, page_width * value / 100)
        item._apply_size(new_width, item.rect().height() * (new_width / item.rect().width()))

    def _sync_controls(self) -> None:
        item = self._selected_object()
        self._block = True
        self.text_group.setVisible(isinstance(item, TextItem))
        self.image_group.setVisible(isinstance(item, ImageItem))
        if isinstance(item, TextItem):
            self.font_combo.setCurrentFont(QFont(item._font.family()))
            self.size_spin.setValue(int(round(item.size_pt)))
        elif isinstance(item, ImageItem):
            page_width = self._background.pixmap().width() if self._background else 1
            percent = max(5, min(100, round(item.rect().width() * 100 / page_width)))
            self.width_spin.setValue(percent)
        self._block = False

    def _sync_groups(self) -> None:
        item = self._selected_object()
        self.text_group.setVisible(isinstance(item, TextItem))
        self.image_group.setVisible(isinstance(item, ImageItem))

    def _build_items(self) -> list[dict]:
        items = []
        for item in self.scene.items():
            if not isinstance(item, (ImageItem, TextItem)): continue
            rect = item.sceneBoundingRect()
            coords = [round(rect.x() / self.zoom, 2), round(rect.y() / self.zoom, 2), round((rect.x() + rect.width()) / self.zoom, 2), round((rect.y() + rect.height()) / self.zoom, 2)]
            if isinstance(item, ImageItem):
                items.append({"type": "image", "rect": coords, "image": item.path})
            else:
                items.append({"type": "text", "rect": coords, "text": item.text, "font": item._font.family(), "size": round(item.size_pt, 1), "color": _pt_color(item.color)})
        return items

    def _save(self) -> None:
        if self.source is None: return
        items = self._build_items()
        name, _ = QFileDialog.getSaveFileName(self, "Save edited PDF", str(self.source.with_name(f"{self.source.stem}_edited.pdf")), "PDF files (*.pdf)")
        if not name: return
        name = name if name.lower().endswith(".pdf") else name + ".pdf"
        self.status.setText("Processing…")
        worker = FunctionWorker(insert_objects, self.source, Path(name), page_index=self._page_index, items=items)
        worker.signals.result.connect(self._saved)
        worker.signals.error.connect(lambda message, details: QMessageBox.critical(self, "Save failed", message))
        worker.signals.finished.connect(lambda: self.status.setText(f"Saved: {Path(name).name}"))
        QThreadPool.globalInstance().start(worker)

    def _saved(self, output) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(output).parent)))
        self.status.setText(f"Saved: {Path(output).name}")
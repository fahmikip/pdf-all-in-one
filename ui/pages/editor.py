"""Interactive page editor: drag images, resize, and add styled text per page."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from pathlib import Path

import pymupdf
from core.jobs.worker import FunctionWorker
from core.pdf.watermark import insert_objects
from core.utils.validation import validate_pdf
from PySide6.QtCore import QPointF, Qt, QThreadPool, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontMetricsF,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

MOVE = QGraphicsItem.GraphicsItemFlag.ItemIsMovable
SELECTABLE = QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
GEOMETRY = QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
SELECT_CHANGE = QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged

HANDLE_COLOR = QColor("#2563eb")
HANDLE_SIZE = 10.0
MIN_SIZE = 20.0
BASE_Z = 10

ROTATIONS = ("0", "90", "180", "270")
ALIGNMENTS = ("left", "center", "right")

COALESCE_LABELS = {
    "Pindahkan atau ubah ukuran objek",
    "Ubah ukuran gambar",
    "Ubah opasitas",
    "Ubah rotasi",
    "Ubah properti teks",
}


def _pt_color(color: QColor) -> list[int]:
    return [color.red(), color.green(), color.blue()]


class HandleItem(QGraphicsRectItem):
    def __init__(self, owner: ObjectItem, anchor: str) -> None:
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
        self.setZValue(BASE_Z)
        self.setTransformOriginPoint(self.rect().center())
        self._handles: dict[str, HandleItem] = {}
        self._resizable = True
        self.uid = uuid.uuid4().hex
        self.before_change: Callable[[], None] | None = None
        self.after_change: Callable[[], None] | None = None
        self._build_handles()

    def _build_handles(self) -> None:
        rect = self.rect()
        for anchor, point in (
            ("tl", (0.0, 0.0)),
            ("tr", (rect.width(), 0.0)),
            ("br", (rect.width(), rect.height())),
            ("bl", (0.0, rect.height())),
        ):
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
        width = rect.width()
        height = rect.height()
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
        self.setTransformOriginPoint(self.rect().center())
        rect = self.rect()
        positions = {
            "tl": (0.0, 0.0),
            "tr": (rect.width(), 0.0),
            "br": (rect.width(), rect.height()),
            "bl": (0.0, rect.height()),
        }
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
        # PySide6's QPainter binding accepts a QRect target for QPixmap, not QRectF.
        # QGraphicsRectItem.rect() is a QRectF, so convert it before drawing.
        painter.drawPixmap(self.rect().toAlignedRect(), self.pixmap)
        if self.isSelected():
            painter.setPen(QPen(HANDLE_COLOR, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect())

    def to_dict(self) -> dict:
        pos = self.pos()
        return {
            "uid": self.uid,
            "type": "image",
            "path": self.path,
            "x": pos.x(),
            "y": pos.y(),
            "width": self.rect().width(),
            "height": self.rect().height(),
            "rotation": self.rotation(),
            "opacity": self.opacity(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> ImageItem:
        pixmap = QPixmap(data["path"])
        if pixmap.isNull():
            pixmap = QPixmap(int(data.get("width", 1) or 1), int(data.get("height", 1) or 1))
            pixmap.fill(QColor("#9ca3af"))
        item = cls(data["x"], data["y"], data["width"], data["height"], data["path"], pixmap)
        item.setRotation(data.get("rotation", 0))
        item.setOpacity(data.get("opacity", 1.0))
        item.uid = data.get("uid", item.uid)
        return item


class TextItem(ObjectItem):
    def __init__(self, x: float, y: float, text: str, family: str, size_pt: float, color: QColor, zoom: float) -> None:
        super().__init__(x, y, 1, 1)
        self.text = text
        self.size_pt = size_pt
        self.zoom = zoom
        self.color = QColor(color)
        self.align = "left"
        self._resizable = False
        self._set_handles(False)
        self._font = QFont(family)
        self._font.setPointSizeF(size_pt * zoom * 0.75)
        self._update_glyphs()

    def _update_glyphs(self) -> None:
        metrics = QFontMetricsF(self._font)
        bounds = metrics.boundingRect(self.text)
        self.setRect(4, 4, max(bounds.width() + 8, 20), max(bounds.height() + 8, 14))
        self.setTransformOriginPoint(self.rect().center())

    def mouseDoubleClickEvent(self, event) -> None:
        new_text, ok = QInputDialog.getText(None, "Edit Teks", "Teks:", text=self.text)
        if ok and new_text != self.text:
            if self.before_change is not None:
                self.before_change()
            self.text = new_text
            self._update_glyphs()
            self.update()
            if self.after_change is not None:
                self.after_change()
        event.accept()

    def apply_style(self, family: str, size_pt: float, color: QColor, align: str = "left") -> None:
        self.size_pt = size_pt
        self.color = QColor(color)
        self.align = align
        self._font = QFont(family)
        self._font.setPointSizeF(size_pt * self.zoom * 0.75)
        self._update_glyphs()
        self.update()

    def to_dict(self) -> dict:
        pos = self.pos()
        return {
            "uid": self.uid,
            "type": "text",
            "text": self.text,
            "font": self._font.family(),
            "size": round(self.size_pt, 1),
            "color": _pt_color(self.color),
            "align": self.align,
            "x": pos.x(),
            "y": pos.y(),
            "width": self.rect().width(),
            "height": self.rect().height(),
            "rotation": self.rotation(),
            "opacity": self.opacity(),
        }

    @classmethod
    def from_dict(cls, data: dict, zoom: float) -> TextItem:
        item = cls(
            data["x"],
            data["y"],
            data["text"],
            data["font"],
            data["size"],
            QColor(*data["color"]),
            zoom,
        )
        item.align = data.get("align", "left")
        item.setRotation(data.get("rotation", 0))
        item.setOpacity(data.get("opacity", 1.0))
        item.uid = data.get("uid", item.uid)
        return item

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setFont(self._font)
        painter.setPen(self.color)
        align = {
            "left": Qt.AlignmentFlag.AlignLeft,
            "center": Qt.AlignmentFlag.AlignHCenter,
            "right": Qt.AlignmentFlag.AlignRight,
        }.get(self.align, Qt.AlignmentFlag.AlignLeft)
        painter.drawText(self.rect(), align | Qt.AlignmentFlag.AlignVCenter, self.text)
        if self.isSelected():
            painter.setPen(QPen(HANDLE_COLOR, 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.rect())


class _CanvasView(QGraphicsView):
    def __init__(self, scene: QGraphicsScene, editor: EditorPage) -> None:
        super().__init__(scene)
        self._editor = editor

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.position().toPoint())
            is_object = isinstance(item, ObjectItem)
            is_object_child = item is not None and isinstance(item.parentItem(), ObjectItem)
            if is_object or is_object_child:
                self._editor.begin_mutation("Pindahkan atau ubah ukuran objek")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self._editor.end_mutation()


class EditorPage(QWidget):
    IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
    GUIDE_TEXT = "Pilih PDF → Tambah objek → Atur posisi → Simpan PDF"

    def __init__(self) -> None:
        super().__init__()
        self.source: Path | None = None
        self.zoom = 1.0
        self.page_objects: dict[int, list[ObjectItem]] = {}
        self._page_index = 0
        self._pages: dict[int, QPixmap] = {}
        self._background: QGraphicsPixmapItem | None = None
        self._block = False
        self._text_color = QColor("#111827")
        self._undo_stack: list[tuple[str, dict]] = []
        self._redo_stack: list[tuple[str, dict]] = []
        self._last_push_ts = 0.0
        self._drag_prestate: dict | None = None
        self._drag_label = ""
        self._drag_geometry: dict[int, tuple[float, float, float, float, float]] = {}
        self._build_ui()
        self._sync_controls()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        choose = QPushButton("Pilih PDF")
        choose.setObjectName("ghost")
        choose.clicked.connect(self._choose_pdf)
        top.addWidget(choose)
        self.source_label = QLabel("Belum ada PDF dipilih")
        self.source_label.setObjectName("muted")
        top.addWidget(self.source_label, 1)
        top.addWidget(QLabel("Halaman"))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setEnabled(False)
        self.page_spin.valueChanged.connect(self._switch_page)
        top.addWidget(self.page_spin)
        self.save_btn = QPushButton("Simpan PDF")
        self.save_btn.setObjectName("success")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        top.addWidget(self.save_btn)
        root.addLayout(top)

        middle = QHBoxLayout()
        controls = QVBoxLayout()
        hint = QLabel(self.GUIDE_TEXT)
        hint.setObjectName("muted")
        controls.addWidget(hint)

        actions = QHBoxLayout()
        self.add_image_btn = QPushButton("Tambah Gambar")
        self.add_image_btn.setObjectName("info")
        self.add_image_btn.setEnabled(False)
        self.add_image_btn.clicked.connect(self._add_image)
        actions.addWidget(self.add_image_btn)
        self.add_text_btn = QPushButton("Tambah Teks")
        self.add_text_btn.setObjectName("success")
        self.add_text_btn.setEnabled(False)
        self.add_text_btn.clicked.connect(self._add_text)
        actions.addWidget(self.add_text_btn)
        delete = QPushButton("Hapus")
        delete.setObjectName("danger")
        delete.clicked.connect(self._delete_selected)
        actions.addWidget(delete)
        controls.addLayout(actions)

        history = QHBoxLayout()
        self.undo_btn = QPushButton("Undo (Ctrl+Z)")
        self.undo_btn.setObjectName("ghost")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self._undo)
        history.addWidget(self.undo_btn)
        self.redo_btn = QPushButton("Redo (Ctrl+Y)")
        self.redo_btn.setObjectName("ghost")
        self.redo_btn.setEnabled(False)
        self.redo_btn.clicked.connect(self._redo)
        history.addWidget(self.redo_btn)
        controls.addLayout(history)

        list_group = QWidget()
        list_form = QFormLayout(list_group)
        list_form.setContentsMargins(0, 8, 0, 0)
        self.object_list = QListWidget()
        self.object_list.setMaximumHeight(180)
        self.object_list.currentItemChanged.connect(self._select_from_list)
        list_form.addRow(QLabel("Objek halaman aktif"), self.object_list)
        layer_row = QHBoxLayout()
        self.raise_btn = QPushButton("Naikkan Layer")
        self.raise_btn.setEnabled(False)
        self.raise_btn.clicked.connect(self._raise_layer)
        layer_row.addWidget(self.raise_btn)
        self.lower_btn = QPushButton("Turunkan Layer")
        self.lower_btn.setEnabled(False)
        self.lower_btn.clicked.connect(self._lower_layer)
        layer_row.addWidget(self.lower_btn)
        list_form.addRow(layer_row)
        controls.addWidget(list_group)

        self.text_group = QWidget()
        text_form = QFormLayout(self.text_group)
        text_form.setContentsMargins(0, 8, 0, 0)
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self._apply_text_style)
        text_form.addRow("Font", self.font_combo)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 300)
        self.size_spin.setValue(16)
        self.size_spin.valueChanged.connect(self._apply_text_style)
        text_form.addRow("Ukuran (pt)", self.size_spin)
        self.color_btn = QPushButton("Hitam")
        self.color_btn.clicked.connect(self._pick_color)
        self._refresh_color_btn()
        text_form.addRow("Warna", self.color_btn)
        self.align_combo = QComboBox()
        self.align_combo.addItems(ALIGNMENTS)
        self.align_combo.currentTextChanged.connect(self._apply_text_style)
        text_form.addRow("Perataan", self.align_combo)
        controls.addWidget(self.text_group)

        self.image_group = QWidget()
        image_form = QFormLayout(self.image_group)
        image_form.setContentsMargins(0, 8, 0, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(5, 100)
        self.width_spin.setSuffix(" % halaman")
        self.width_spin.setValue(50)
        self.width_spin.valueChanged.connect(self._apply_image_width)
        image_form.addRow("Ukuran", self.width_spin)
        controls.addWidget(self.image_group)

        self.common_group = QWidget()
        common_form = QFormLayout(self.common_group)
        common_form.setContentsMargins(0, 8, 0, 0)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(100)
        self.opacity_spin.setSuffix(" %")
        self.opacity_spin.valueChanged.connect(self._apply_opacity)
        common_form.addRow("Opasitas", self.opacity_spin)
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(ROTATIONS)
        self.rotation_combo.currentTextChanged.connect(self._apply_rotation)
        common_form.addRow("Rotasi", self.rotation_combo)
        controls.addWidget(self.common_group)

        controls.addStretch(1)
        middle.addLayout(controls)

        self.scene = QGraphicsScene(self)
        self.view = _CanvasView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setBackgroundBrush(QColor("#1f2430"))
        self.scene.selectionChanged.connect(self._sync_controls)
        middle.addWidget(self.view, 1)
        root.addLayout(middle, 1)

        self.status = QLabel(self.GUIDE_TEXT)
        self.status.setObjectName("muted")
        root.addWidget(self.status)

        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self._undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, activated=self._redo)
        delete_shortcut = QShortcut(QKeySequence.StandardKey.Delete, self, activated=self._delete_selected)
        delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

    def _refresh_color_btn(self) -> None:
        self.color_btn.setStyleSheet(
            f"background-color: {self._text_color.name()}; color: {'white' if self._text_color.lightness() < 128 else 'black'}; border-radius: 4px;"
        )

    def _choose_pdf(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Pilih PDF", "", "Berkas PDF (*.pdf)")
        if not name:
            return
        self.load_pdf(name)

    def load_pdf(self, path: str | Path) -> bool:
        """Load *path* into the canvas and reset objects from the previous PDF."""
        try:
            info = validate_pdf(path)
            with pymupdf.open(info.path) as document:
                width = document[0].rect.width
        except Exception as exc:
            QMessageBox.warning(self, "Tidak Dapat Membuka PDF", str(exc))
            return False
        self.source = info.path
        self.zoom = max(1.0, min(2.5, 860 / width))
        self._pages = {}
        self.page_objects = {}
        self._background = None
        self._undo_stack = []
        self._redo_stack = []
        self._drag_prestate = None
        self._last_push_ts = 0.0
        self.scene.clear()
        self.source_label.setText(self.source.name)
        self.page_spin.blockSignals(True)
        self.page_spin.setRange(1, info.pages)
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.page_spin.setEnabled(True)
        self.add_image_btn.setEnabled(True)
        self.add_text_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self._page_index = 0
        self._load_page(0)
        self._refresh_object_list()
        self._sync_controls()
        self._update_history_buttons()
        self.status.setText(
            f"{info.pages} halaman dimuat. Seret objek; ubah ukuran dengan titik sudut; simpan ke PDF baru."
        )
        return True

    def _render_page(self, index: int) -> QPixmap:
        if index in self._pages:
            return self._pages[index]
        with pymupdf.open(self.source) as document:
            pixmap = document[index].get_pixmap(matrix=pymupdf.Matrix(self.zoom, self.zoom), alpha=False)
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
        if self.source is None:
            return
        if index - 1 == self._page_index:
            return
        for item in list(self.scene.items()):
            if isinstance(item, (ObjectItem, QGraphicsPixmapItem)):
                self.scene.removeItem(item)
        self.scene.clear()
        self._page_index = index - 1
        self._load_page(self._page_index)
        self._refresh_object_list()
        self._sync_controls()

    def _object_by_uid(self, uid: str):
        for item in self.page_objects.get(self._page_index, []):
            if item.uid == uid:
                return item
        return None

    def _selected_object(self):
        for item in self.scene.selectedItems():
            if isinstance(item, ObjectItem):
                return item
        return None

    def begin_mutation(self, label: str) -> None:
        if self._drag_prestate is not None:
            return
        self._drag_prestate = self._snapshot()
        self._drag_label = label
        self._drag_geometry = {
            id(item): (
                item.pos().x(),
                item.pos().y(),
                item.rect().width(),
                item.rect().height(),
                item.rotation(),
                item.opacity(),
            )
            for objects in self.page_objects.values()
            for item in objects
        }

    def end_mutation(self) -> None:
        if self._drag_prestate is None:
            return
        changed = False
        for objects in self.page_objects.values():
            for item in objects:
                before = self._drag_geometry.get(id(item))
                if before is None:
                    continue
                current = (
                    item.pos().x(),
                    item.pos().y(),
                    item.rect().width(),
                    item.rect().height(),
                    item.rotation(),
                    item.opacity(),
                )
                if any(abs(left - right) > 0.01 for left, right in zip(before, current, strict=True)):
                    changed = True
                    break
            if changed:
                break
        if changed:
            self._push_snapshot(self._drag_prestate, self._drag_label)
        self._drag_prestate = None
        self._drag_geometry = {}

    def _push_history(self, label: str) -> None:
        self._push_snapshot(self._snapshot(), label)

    def _push_snapshot(self, state: dict, label: str) -> None:
        now = time.monotonic()
        same_label = bool(self._undo_stack) and self._undo_stack[-1][0] == label
        if same_label and label in COALESCE_LABELS and now - self._last_push_ts < 1.5:
            self._undo_stack[-1] = (label, state)
        else:
            self._undo_stack.append((label, state))
        del self._undo_stack[:-200]
        self._redo_stack.clear()
        self._last_push_ts = now
        self._update_history_buttons()

    def _undo(self) -> None:
        if not self._undo_stack or self.source is None:
            return
        label, state = self._undo_stack.pop()
        self._redo_stack.append((label, self._snapshot()))
        del self._redo_stack[:-200]
        self._restore(state)
        self._update_history_buttons()
        self.status.setText(f"Undo: {label}")

    def _redo(self) -> None:
        if not self._redo_stack or self.source is None:
            return
        label, state = self._redo_stack.pop()
        self._undo_stack.append((label, self._snapshot()))
        del self._undo_stack[:-200]
        self._restore(state)
        self._update_history_buttons()
        self.status.setText(f"Redo: {label}")

    def _update_history_buttons(self) -> None:
        self.undo_btn.setEnabled(bool(self._undo_stack))
        self.redo_btn.setEnabled(bool(self._redo_stack))

    def _snapshot(self) -> dict:
        selected = self._selected_object()
        return {
            "pages": {
                page: [item.to_dict() for item in objects] for page, objects in self.page_objects.items() if objects
            },
            "page": self._page_index,
            "selected": selected.uid if selected else None,
        }

    def _restore(self, state: dict) -> None:
        pages = {
            page: [self._rebuild_item(data) for data in descriptors] for page, descriptors in state["pages"].items()
        }
        self.page_objects = pages
        self.scene.clear()
        self._page_index = state["page"]
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self._page_index + 1)
        self.page_spin.blockSignals(False)
        self._load_page(self._page_index)
        self._reindex_zvalues()
        self._refresh_object_list()
        if state.get("selected"):
            selected = self._object_by_uid(state["selected"])
            if selected is not None:
                selected.setSelected(True)
        self._sync_controls()

    def _rebuild_item(self, data: dict) -> ObjectItem:
        if data["type"] == "image":
            item: ObjectItem = ImageItem.from_dict(data)
        else:
            item = TextItem.from_dict(data, self.zoom)
        item.before_change = lambda: self._push_history("Edit isi teks")
        item.after_change = self._refresh_object_list
        return item

    def _add_image(self) -> None:
        if self.source is None:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        name, _ = QFileDialog.getOpenFileName(self, "Pilih foto atau gambar", "", self.IMAGE_FILTER)
        if not name:
            return
        pixmap = QPixmap(name)
        if pixmap.isNull():
            QMessageBox.warning(self, "Tidak Dapat Membuka Gambar", "File gambar tersebut tidak dapat dibaca.")
            return
        self._push_history("Tambahkan gambar")
        page_pixmap = self._render_page(self._page_index)
        width = page_pixmap.width() * 0.5
        height = width * pixmap.height() / pixmap.width()
        x = (page_pixmap.width() - width) / 2
        y = (page_pixmap.height() - height) / 2
        path = str(Path(name).resolve())
        item = ImageItem(x, y, width, height, path, pixmap)
        self.scene.addItem(item)
        self.page_objects.setdefault(self._page_index, []).append(item)
        self._reindex_zvalues()
        self.scene.clearSelection()
        item.setSelected(True)
        self._refresh_object_list()
        self.status.setText("Gambar ditambahkan. Seret untuk memposisikan; gunakan titik sudut untuk mengubah ukuran.")

    def _add_text(self) -> None:
        if self.source is None:
            QMessageBox.information(self, "Pilih PDF", "Pilih PDF terlebih dahulu.")
            return
        text, accepted = QInputDialog.getMultiLineText(
            self,
            "Tambah Teks",
            "Teks yang ingin ditambahkan:",
        )
        text = text.strip()
        if not accepted or not text:
            return
        self._push_history("Tambahkan teks")
        page_pixmap = self._render_page(self._page_index)
        item = TextItem(
            page_pixmap.width() / 2 - 60,
            page_pixmap.height() / 2 - 20,
            text,
            self.font_combo.currentFont().family(),
            self.size_spin.value(),
            self._text_color,
            self.zoom,
        )
        item.before_change = lambda: self._push_history("Edit isi teks")
        item.after_change = self._refresh_object_list
        self.scene.addItem(item)
        self.page_objects.setdefault(self._page_index, []).append(item)
        self._reindex_zvalues()
        self.scene.clearSelection()
        item.setSelected(True)
        self._refresh_object_list()
        self.status.setText("Teks ditambahkan. Seret untuk memposisikan; klik dua kali untuk mengubah isinya.")

    def _delete_selected(self) -> None:
        items = [item for item in self.scene.selectedItems() if isinstance(item, ObjectItem)]
        if not items:
            QMessageBox.information(
                self, "Tidak Ada Objek", "Pilih objek di kanvas atau pada daftar objek terlebih dahulu."
            )
            return
        self._push_history("Hapus objek")
        objects = self.page_objects.get(self._page_index, [])
        for item in items:
            self.scene.removeItem(item)
            if item in objects:
                objects.remove(item)
        self._reindex_zvalues()
        self._refresh_object_list()
        self._sync_controls()
        self.status.setText("Objek dihapus.")

    def _apply_text_style(self, *_args) -> None:
        if self._block:
            return
        item = self._selected_object()
        if not isinstance(item, TextItem):
            return
        self._push_history("Ubah properti teks")
        item.apply_style(
            self.font_combo.currentFont().family(),
            self.size_spin.value(),
            self._text_color,
            self.align_combo.currentText(),
        )
        self._refresh_object_list()

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(self._text_color, self, "Warna teks")
        if not color.isValid():
            return
        self._text_color = color
        self._refresh_color_btn()
        self._apply_text_style()

    def _apply_image_width(self, value: int) -> None:
        if self._block or self._background is None:
            return
        item = self._selected_object()
        if not isinstance(item, ImageItem):
            return
        self._push_history("Ubah ukuran gambar")
        page_width = self._background.pixmap().width()
        new_width = max(MIN_SIZE, page_width * value / 100)
        item._apply_size(new_width, item.rect().height() * (new_width / item.rect().width()))

    def _apply_opacity(self, value: int) -> None:
        if self._block:
            return
        item = self._selected_object()
        if not isinstance(item, ObjectItem):
            return
        self._push_history("Ubah opasitas")
        item.setOpacity(value / 100)

    def _apply_rotation(self, value: str) -> None:
        if self._block:
            return
        item = self._selected_object()
        if not isinstance(item, ObjectItem):
            return
        self._push_history("Ubah rotasi")
        item.setRotation(int(value))

    def _sync_controls(self) -> None:
        item = self._selected_object()
        self._block = True
        self.text_group.setVisible(isinstance(item, TextItem))
        self.image_group.setVisible(isinstance(item, ImageItem))
        self.common_group.setVisible(isinstance(item, ObjectItem))
        if isinstance(item, TextItem):
            self.font_combo.setCurrentFont(QFont(item._font.family()))
            self.size_spin.setValue(round(item.size_pt))
            self.align_combo.setCurrentText(item.align)
        elif isinstance(item, ImageItem):
            page_width = self._background.pixmap().width() if self._background else 1
            percent = max(5, min(100, round(item.rect().width() * 100 / page_width)))
            self.width_spin.setValue(percent)
        if isinstance(item, ObjectItem):
            self.opacity_spin.setValue(round(item.opacity() * 100))
            rotation = ROTATIONS[0] if not item.rotation() else str(int(item.rotation()) % 360)
            self.rotation_combo.setCurrentText(rotation)
        self._block = False
        self._refresh_object_list()

    def _refresh_object_list(self) -> None:
        objects = self.page_objects.get(self._page_index, [])
        selected = self._selected_object()
        self.object_list.blockSignals(True)
        self.object_list.clear()
        for index, item in enumerate(objects, start=1):
            row = QListWidgetItem(self._object_label(item, index))
            row.setData(Qt.ItemDataRole.UserRole, item.uid)
            self.object_list.addItem(row)
            if selected is not None and item.uid == selected.uid:
                self.object_list.setCurrentRow(index - 1)
        self.object_list.blockSignals(False)
        self.raise_btn.setEnabled(bool(objects))
        self.lower_btn.setEnabled(bool(objects))

    def _object_label(self, item: ObjectItem, index: int) -> str:
        if isinstance(item, ImageItem):
            return f"{index}. Gambar: {Path(item.path).name}"
        preview = item.text.replace("\n", " ").strip()
        if len(preview) > 24:
            preview = preview[:24] + "…"
        return f"{index}. Teks: {preview}"

    def _select_from_list(self, current, _previous=None) -> None:
        if self._block or current is None:
            return
        uid = current.data(Qt.ItemDataRole.UserRole)
        item = self._object_by_uid(uid)
        if item is None:
            return
        for other in self.page_objects.get(self._page_index, []):
            other.setSelected(other is item)

    def _raise_layer(self) -> None:
        objects = self.page_objects.get(self._page_index, [])
        item = self._selected_object()
        if item is None or item not in objects:
            return
        self._push_history("Ubah urutan layer")
        index = objects.index(item)
        objects.pop(index)
        objects.append(item)
        self._reindex_zvalues()
        self._refresh_object_list()
        self.status.setText(f"{type(item).__name__} dipindah ke layer paling depan.")

    def _lower_layer(self) -> None:
        objects = self.page_objects.get(self._page_index, [])
        item = self._selected_object()
        if item is None or item not in objects:
            return
        self._push_history("Ubah urutan layer")
        index = objects.index(item)
        objects.pop(index)
        objects.insert(0, item)
        self._reindex_zvalues()
        self._refresh_object_list()
        self.status.setText(f"{type(item).__name__} dipindah ke layer paling belakang.")

    def _reindex_zvalues(self) -> None:
        for index, item in enumerate(self.page_objects.get(self._page_index, [])):
            item.setZValue(BASE_Z + index)

    def _export_item(self, item: ObjectItem) -> dict:
        width = item.rect().width()
        height = item.rect().height()
        center_x = item.pos().x() + width / 2
        center_y = item.pos().y() + height / 2
        rotation = item.rotation()
        pdf_width = width / self.zoom
        pdf_height = height / self.zoom
        if rotation in (90.0, 270.0):
            pdf_width, pdf_height = pdf_height, pdf_width
        x0 = center_x / self.zoom - pdf_width / 2
        y0 = center_y / self.zoom - pdf_height / 2
        base: dict = {
            "uid": item.uid,
            "type": "image" if isinstance(item, ImageItem) else "text",
            "rect": [round(x0, 2), round(y0, 2), round(x0 + pdf_width, 2), round(y0 + pdf_height, 2)],
            "rotation": int(rotation),
            "opacity": round(item.opacity(), 2),
        }
        if isinstance(item, ImageItem):
            base["image"] = item.path
        else:
            base["text"] = item.text
            base["font"] = item._font.family()
            base["size"] = round(item.size_pt, 1)
            base["color"] = _pt_color(item.color)
            base["align"] = item.align
        return base

    def _build_items(self) -> dict[int, list[dict]]:
        return {
            page: [self._export_item(item) for item in objects]
            for page, objects in self.page_objects.items()
            if objects
        }

    def _save(self) -> None:
        if self.source is None:
            return
        page_items = self._build_items()
        if not page_items:
            QMessageBox.information(self, "Tidak Ada Objek", "Tambahkan gambar atau teks ke halaman terlebih dahulu.")
            return
        name, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan PDF hasil edit",
            str(self.source.with_name(f"{self.source.stem}_edited.pdf")),
            "Berkas PDF (*.pdf)",
        )
        if not name:
            return
        name = name if name.lower().endswith(".pdf") else name + ".pdf"
        self.status.setText("Memproses…")
        worker = FunctionWorker(insert_objects, self.source, Path(name), page_items=page_items)
        worker.signals.result.connect(self._saved)
        worker.signals.error.connect(self._save_failed)
        QThreadPool.globalInstance().start(worker)

    def _save_failed(self, message: str, _details: str) -> None:
        self.status.setText("Penyimpanan gagal.")
        QMessageBox.critical(self, "Penyimpanan Gagal", message)

    def _saved(self, output) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(output).parent)))
        self.status.setText(f"Tersimpan: {Path(output).name}")

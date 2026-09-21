import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pymupdf
from core.pdf.watermark import insert_objects
from PIL import Image
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog
from ui.pages.edit import EditPage
from ui.pages.editor import EditorPage, ImageItem, TextItem


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _add_photo(tmp_path: Path) -> Path:
    photo = tmp_path / "photo.png"
    Image.new("RGBA", (60, 30), (20, 120, 220, 255)).save(photo)
    return photo


def test_editor_tab_exists(sample_pdf: Path) -> None:
    _app()
    edit = EditPage()
    assert any(isinstance(edit.tabs.widget(i), EditorPage) for i in range(edit.tabs.count()))
    assert edit.load_pdf(sample_pdf)
    assert edit.editor.source == sample_pdf.resolve()


def test_editor_export_and_place_roundtrip(sample_pdf: Path, tmp_path: Path) -> None:
    _app()
    editor = EditorPage()
    with pymupdf.open(sample_pdf) as document:
        editor.zoom = max(1.0, min(2.5, 860 / document[0].rect.width))
    editor.source = sample_pdf
    editor._page_index = 0
    editor._pages = {}
    editor.scene.clear()
    editor._load_page(0)

    photo = _add_photo(tmp_path)
    pixmap = QPixmap(str(photo))
    image_item = ImageItem(30.0, 40.0, 90.0, 45.0, str(photo), pixmap)
    text_item = TextItem(20.0, 10.0, "Teks Editor", "Arial", 18, QColor("#ff2222"), editor.zoom)
    editor.scene.addItem(image_item)
    editor.scene.addItem(text_item)
    editor.page_objects[0] = [image_item, text_item]

    page_items = editor._build_items()
    assert set(page_items) == {0}
    assert len(page_items[0]) == 2
    image_item_dict = next(item for item in page_items[0] if item["type"] == "image")
    text_item_dict = next(item for item in page_items[0] if item["type"] == "text")
    assert image_item_dict["image"] == str(photo.resolve())
    assert text_item_dict["text"] == "Teks Editor"
    assert text_item_dict["color"] == [255, 34, 34]

    output = insert_objects(sample_pdf, tmp_path / "editor.pdf", page_items=page_items)
    with pymupdf.open(output) as document:
        assert len(document[0].get_images()) >= 1
        assert "Teks Editor" in document[0].get_text()


def test_image_item_paints_with_qrect_target(tmp_path: Path) -> None:
    _app()
    photo = _add_photo(tmp_path)
    item = ImageItem(0.0, 0.0, 40.0, 20.0, str(photo), QPixmap(str(photo)))
    canvas = QImage(60, 40, QImage.Format.Format_ARGB32)
    canvas.fill(0)
    painter = QPainter(canvas)
    try:
        item.paint(painter, None)
    finally:
        painter.end()
    assert canvas.pixelColor(10, 10).alpha() == 255


def test_add_text_prompts_for_text_before_creating_item(sample_pdf: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    assert editor.load_pdf(sample_pdf)
    monkeypatch.setattr(QInputDialog, "getMultiLineText", lambda *_args, **_kwargs: ("Catatan", True))

    editor._add_text()

    items = editor.page_objects[0]
    assert len(items) == 1
    assert isinstance(items[0], TextItem)
    assert items[0].text == "Catatan"


def test_objects_survive_page_switching(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    editor.load_pdf(sample_pdf)
    assert editor.page_spin.maximum() == 3
    photo = _add_photo(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_args, **_kwargs: (str(photo), ""))
    monkeypatch.setattr(QInputDialog, "getMultiLineText", lambda *_args, **_kwargs: ("Teks halaman kedua", True))

    editor._add_image()
    assert len(editor.page_objects.get(0, [])) == 1

    editor.page_spin.setValue(2)
    assert editor._page_index == 1
    assert 0 in editor.page_objects
    scene_images = [item for item in editor.scene.items() if isinstance(item, ImageItem)]
    assert scene_images == []
    assert len([item for item in editor.scene.items() if isinstance(item, TextItem)]) == 0

    editor._add_text()
    assert len(editor.page_objects.get(1, [])) == 1

    editor.page_spin.setValue(1)
    assert editor._page_index == 0
    scene_images = [item for item in editor.scene.items() if isinstance(item, ImageItem)]
    assert len(scene_images) == 1
    assert len(editor.page_objects) == 2


def test_undo_redo_add_and_delete(sample_pdf: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    editor.load_pdf(sample_pdf)
    monkeypatch.setattr(QInputDialog, "getMultiLineText", lambda *_args, **_kwargs: ("Halo", True))

    editor._add_text()
    assert len(editor.page_objects.get(0, [])) == 1

    editor._undo()
    assert editor.page_objects.get(0) is None

    editor._redo()
    assert len(editor.page_objects.get(0, [])) == 1

    item = editor.page_objects[0][0]
    item.setSelected(True)
    editor._delete_selected()
    assert editor.page_objects.get(0) == []

    editor._undo()
    assert len(editor.page_objects.get(0, [])) == 1


def test_undo_redo_move_object(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    editor.load_pdf(sample_pdf)
    photo = _add_photo(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_args, **_kwargs: (str(photo), ""))

    editor._add_image()
    item = editor.page_objects[0][0]
    initial = item.pos()

    editor.begin_mutation("Pindahkan objek")
    item.setPos(initial.x() + 30, initial.y() + 20)
    editor.end_mutation()

    assert editor._undo_stack
    editor._undo()
    restored = editor.page_objects.get(0, [])[0]
    assert restored.uid == item.uid
    assert (restored.pos().x(), restored.pos().y()) == (initial.x(), initial.y())


def test_undo_redo_text_edit(sample_pdf: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    editor.load_pdf(sample_pdf)
    monkeypatch.setattr(QInputDialog, "getMultiLineText", lambda *_args, **_kwargs: ("Lama", True))
    editor._add_text()
    item = editor.page_objects[0][0]

    monkeypatch.setattr(QInputDialog, "getText", lambda *_args, **_kwargs: ("Baru", True))

    class _Event:
        def accept(self) -> None:
            pass

    item.mouseDoubleClickEvent(_Event())
    assert item.text == "Baru"

    editor._undo()
    rebuilt = editor.page_objects.get(0, [])[0]
    assert rebuilt.text == "Lama"


def test_layer_order_front_and_back(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    editor.load_pdf(sample_pdf)
    photo = _add_photo(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_args, **_kwargs: (str(photo), ""))
    monkeypatch.setattr(QInputDialog, "getMultiLineText", lambda *_args, **_kwargs: ("Layer Teks", True))

    editor._add_image()
    editor._add_image()
    editor._add_text()

    objects = editor.page_objects[0]
    assert objects[-1] is editor._selected_object()

    editor._lower_layer()
    objects = editor.page_objects[0]
    assert objects[0] is editor._selected_object()
    z_values = [item.zValue() for item in objects]
    assert z_values == sorted(z_values)

    editor._raise_layer()
    objects = editor.page_objects[0]
    assert objects[-1] is editor._selected_object()
    z_values = [item.zValue() for item in objects]
    assert z_values == sorted(z_values)


def test_export_all_objects_across_pages(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    editor.load_pdf(sample_pdf)
    photo = _add_photo(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_args, **_kwargs: (str(photo), ""))
    monkeypatch.setattr(QInputDialog, "getMultiLineText", lambda *_args, **_kwargs: ("Teks halaman kedua", True))

    editor._add_image()
    editor.page_spin.setValue(2)
    editor._add_text()

    page_items = editor._build_items()
    assert set(page_items) == {0, 1}
    assert page_items[0][0]["type"] == "image"
    assert page_items[1][0]["type"] == "text"
    assert page_items[1][0]["text"] == "Teks halaman kedua"

    output = insert_objects(sample_pdf, tmp_path / "all_pages.pdf", page_items=page_items)
    with pymupdf.open(output) as document:
        assert len(document[0].get_images()) >= 1
        assert "Teks halaman kedua" in document[1].get_text()
        assert "Teks halaman kedua" not in document[0].get_text()


def test_multiline_text_export_is_not_dropped(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    editor.load_pdf(sample_pdf)
    monkeypatch.setattr(QInputDialog, "getMultiLineText", lambda *_args, **_kwargs: ("Baris satu\nBaris dua", True))

    editor._add_text()

    page_items = editor._build_items()
    output = insert_objects(sample_pdf, tmp_path / "multiline.pdf", page_items=page_items)
    with pymupdf.open(output) as document:
        text = document[0].get_text()
        assert "Baris satu" in text
        assert "Baris dua" in text


def test_rotated_text_and_image_export(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    _app()
    editor = EditorPage()
    editor.load_pdf(sample_pdf)
    photo = _add_photo(tmp_path)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_args, **_kwargs: (str(photo), ""))
    monkeypatch.setattr(QInputDialog, "getMultiLineText", lambda *_args, **_kwargs: ("Isi miring", True))

    editor._add_image()
    image_item = editor.page_objects[0][0]
    image_item.setRotation(90)
    image_item.setOpacity(0.6)

    editor._add_text()
    text_item = editor.page_objects[0][1]
    text_item.setRotation(90)

    page_items = editor._build_items()
    assert page_items[0][0]["rotation"] == 90
    assert page_items[0][0]["opacity"] == round(image_item.opacity(), 2)
    assert page_items[0][1]["rotation"] == 90

    output = insert_objects(sample_pdf, tmp_path / "rotated.pdf", page_items=page_items)
    with pymupdf.open(output) as document:
        assert len(document[0].get_images()) >= 1
        assert "Isi miring" in document[0].get_text()

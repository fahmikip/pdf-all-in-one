import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import fitz
from PIL import Image
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication

from core.pdf.watermark import insert_objects
from ui.pages.edit import EditPage
from ui.pages.editor import EditorPage, ImageItem, TextItem


def test_editor_tab_exists(sample_pdf: Path) -> None:
    QApplication.instance() or QApplication([])
    edit = EditPage()
    assert any(isinstance(edit.tabs.widget(i), EditorPage) for i in range(edit.tabs.count()))


def test_editor_export_and_place_roundtrip(sample_pdf: Path, tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    editor = EditorPage()
    with fitz.open(sample_pdf) as document:
        editor.zoom = max(1.0, min(2.5, 860 / document[0].rect.width))
    editor.source = sample_pdf
    editor._page_index = 0
    editor._pages = {}
    editor.scene.clear()
    editor._load_page(0)

    photo = tmp_path / "photo.png"; Image.new("RGBA", (60, 30), (20, 120, 220, 255)).save(photo)
    pixmap = QPixmap(str(photo))
    editor.scene.addItem(ImageItem(30.0, 40.0, 90.0, 45.0, str(photo), pixmap))
    editor.scene.addItem(TextItem(20.0, 10.0, "Teks Editor", "Arial", 18, QColor("#ff2222"), editor.zoom))

    items = editor._build_items()
    assert len(items) == 2
    image_item = next(item for item in items if item["type"] == "image")
    text_item = next(item for item in items if item["type"] == "text")
    assert image_item["image"] == str(photo.resolve())
    assert text_item["text"] == "Teks Editor"
    assert text_item["color"] == [255, 34, 34]

    output = insert_objects(sample_pdf, tmp_path / "editor.pdf", page_index=0, items=items)
    with fitz.open(output) as document:
        assert len(document[0].get_images()) >= 1
        assert "Teks Editor" in document[0].get_text()
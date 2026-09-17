import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication
from ui.widgets.signature_pad import SignaturePad, render_signature_image, signature_png_path


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_render_signature_image() -> None:
    strokes = [[QPointF(10, 10), QPointF(40, 60), QPointF(80, 40)]]
    image = render_signature_image(strokes, 320, 120)
    assert not image.isNull()
    assert image.width() == 320
    assert image.height() == 120


def test_render_transparent_background() -> None:
    strokes = [[QPointF(5, 5), QPointF(60, 60)]]
    for pixel in render_signature_image(strokes, 64, 64).pixelColor(0, 0).getRgb()[:3]:
        assert pixel == 0  # transparent background stays empty


def test_signature_png_path() -> None:
    strokes = [[QPointF(5, 5), QPointF(60, 60)]]
    path = signature_png_path(strokes, pad_width=320, pad_height=120)
    try:
        assert path.exists()
        assert path.suffix == ".png"
        assert path.stat().st_size > 0
    finally:
        path.unlink(missing_ok=True)


def test_pad_clear_and_empty() -> None:
    _app()
    pad = SignaturePad()
    assert pad.is_empty()
    assert not pad.has_changes()
    pad.strokes.append([QPointF(1, 1), QPointF(2, 2)])
    assert not pad.is_empty()
    assert pad.has_changes()
    pad.clear()
    assert pad.is_empty()
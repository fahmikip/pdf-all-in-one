from pathlib import Path

import pymupdf
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication


@pytest.fixture(autouse=True)
def _cleanup_qt_widgets():
    """Release Qt widgets between tests to avoid native teardown crashes on Windows."""
    yield
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    document = pymupdf.open()
    for index in range(3):
        page = document.new_page(width=300, height=400)
        page.insert_text((40, 60), f"Page {index + 1}", fontsize=18)
    document.set_metadata({"title": "Original", "author": "Test"})
    document.save(path)
    document.close()
    return path

from pathlib import Path

import pytest

from core.ocr.ocr_engine import OcrUnavailableError, available_languages, find_tesseract, ocr_image


def test_missing_tesseract_is_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("core.ocr.ocr_engine.shutil.which", lambda name: None)
    monkeypatch.setattr("core.ocr.ocr_engine.Path.is_file", lambda self: False)
    assert find_tesseract() is None
    assert available_languages() == []
    with pytest.raises(OcrUnavailableError):
        ocr_image(tmp_path / "image.png", tmp_path / "output.txt")

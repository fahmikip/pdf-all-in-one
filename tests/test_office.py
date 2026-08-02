from pathlib import Path

import pytest
from docx import Document

from core.office.libreoffice_converter import LibreOfficeUnavailableError, find_libreoffice, office_to_pdf
from core.office.pdf_to_word import pdf_to_word


def test_pdf_to_word_extracts_text(sample_pdf: Path, tmp_path: Path) -> None:
    output = pdf_to_word(sample_pdf, tmp_path / "output.docx", include_images=False)
    document = Document(output)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Page 1" in text and "Page 3" in text


def test_missing_libreoffice_has_friendly_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("core.office.libreoffice_converter.shutil.which", lambda name: None)
    monkeypatch.setattr("core.office.libreoffice_converter.Path.is_file", lambda self: False)
    assert find_libreoffice() is None
    with pytest.raises(LibreOfficeUnavailableError):
        office_to_pdf(tmp_path / "document.docx", tmp_path / "document.pdf")

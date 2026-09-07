from pathlib import Path

import fitz
import pytest
from docx import Document
from openpyxl import load_workbook
from PIL import Image

from core.office.libreoffice_converter import LibreOfficeUnavailableError, find_libreoffice, office_to_pdf
from core.office.pdf_to_excel import pdf_to_excel
from core.office.pdf_to_word import pdf_to_word


def test_pdf_to_word_extracts_text(sample_pdf: Path, tmp_path: Path) -> None:
    output = pdf_to_word(sample_pdf, tmp_path / "output.docx", include_images=False)
    document = Document(output)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Page 1" in text and "Page 3" in text


def _content_pdf(path: Path) -> Path:
    document = fitz.open()
    page = document.new_page(width=300, height=400)
    page.insert_text((40, 60), "Item")
    page.insert_text((40, 120), "Pen")
    image = Path(path.parent) / "photo.png"
    Image.new("RGB", (80, 60), (200, 40, 40)).save(image)
    page.insert_image(fitz.Rect(40, 160, 120, 220), filename=str(image))
    document.save(path)
    document.close()
    return path


def test_pdf_to_excel_exports_text_and_images(tmp_path: Path) -> None:
    pdf = _content_pdf(tmp_path / "content.pdf")
    output = pdf_to_excel(pdf, tmp_path / "content.xlsx")
    workbook = load_workbook(output)
    assert workbook.sheetnames == ["Page 1"]
    sheet = workbook.active
    values = [sheet.cell(row=r, column=1).value for r in range(1, 4)]
    assert "Item" in values and "Pen" in values
    assert sheet._images, "expected an embedded image"


def test_pdf_to_excel_empty_page_raises(sample_pdf: Path, tmp_path: Path) -> None:
    blank = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page(width=300, height=400)
    document.save(blank); document.close()
    with pytest.raises(ValueError):
        pdf_to_excel(blank, tmp_path / "out.xlsx")


def test_pdf_to_excel_rejects_non_xlsx(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        pdf_to_excel(sample_pdf, tmp_path / "out.pdf")


def test_missing_libreoffice_has_friendly_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("core.office.libreoffice_converter.shutil.which", lambda name: None)
    monkeypatch.setattr("core.office.libreoffice_converter.Path.is_file", lambda self: False)
    assert find_libreoffice() is None
    with pytest.raises(LibreOfficeUnavailableError):
        office_to_pdf(tmp_path / "document.docx", tmp_path / "document.pdf")

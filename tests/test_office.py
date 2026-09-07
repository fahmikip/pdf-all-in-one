from pathlib import Path

import fitz
import pytest
from docx import Document
from openpyxl import load_workbook

from core.office.libreoffice_converter import LibreOfficeUnavailableError, find_libreoffice, office_to_pdf
from core.office.pdf_to_excel import pdf_to_excel
from core.office.pdf_to_word import pdf_to_word


def test_pdf_to_word_extracts_text(sample_pdf: Path, tmp_path: Path) -> None:
    output = pdf_to_word(sample_pdf, tmp_path / "output.docx", include_images=False)
    document = Document(output)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Page 1" in text and "Page 3" in text


def _table_based_pdf(path: Path) -> Path:
    document = fitz.open()
    page = document.new_page(width=400, height=300)
    for x in (40, 160, 280, 360): page.draw_line(fitz.Point(x, 60), fitz.Point(x, 200), color=(0, 0, 0))
    for y in (60, 100, 140, 180, 200): page.draw_line(fitz.Point(40, y), fitz.Point(360, y), color=(0, 0, 0))
    for word, x, y in (("Item", 40, 80), ("Qty", 160, 80), ("Price", 280, 80), ("Pen", 40, 120), ("2", 160, 120), ("3.5", 280, 120), ("Book", 40, 160), ("1", 160, 160), ("12.0", 280, 160)):
        page.insert_text((x + 6, y + 8), word)
    document.save(path)
    document.close()
    return path


def test_pdf_to_excel_detects_tables(tmp_path: Path) -> None:
    pdf = _table_based_pdf(tmp_path / "table.pdf")
    output = pdf_to_excel(pdf, tmp_path / "table.xlsx")
    workbook = load_workbook(output)
    assert workbook.sheetnames == ["Page 1"]
    sheet = workbook.active
    assert sheet["A1"].value == "Item" and sheet["B1"].value == "Qty"
    assert sheet["A2"].value == "Pen" and sheet["C3"].value == "12.0"


def test_pdf_to_excel_no_tables_raises(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        pdf_to_excel(sample_pdf, tmp_path / "out.xlsx")


def test_pdf_to_excel_rejects_non_xlsx(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        pdf_to_excel(sample_pdf, tmp_path / "out.pdf")


def test_missing_libreoffice_has_friendly_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("core.office.libreoffice_converter.shutil.which", lambda name: None)
    monkeypatch.setattr("core.office.libreoffice_converter.Path.is_file", lambda self: False)
    assert find_libreoffice() is None
    with pytest.raises(LibreOfficeUnavailableError):
        office_to_pdf(tmp_path / "document.docx", tmp_path / "document.pdf")

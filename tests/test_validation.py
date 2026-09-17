from pathlib import Path

import pikepdf
import pytest
from core.utils.validation import ValidationError, parse_page_ranges, validate_pdf


def test_validate_and_parse_ranges(sample_pdf: Path) -> None:
    assert validate_pdf(sample_pdf).pages == 3
    assert parse_page_ranges("1-2, 3, 2", 3) == [0, 1, 2]


def test_invalid_pdf_is_rejected(tmp_path: Path) -> None:
    damaged = tmp_path / "damaged.pdf"
    damaged.write_bytes(b"not a pdf")
    with pytest.raises(ValidationError):
        validate_pdf(damaged)


def test_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_page_ranges("1,4", 3)


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        validate_pdf(tmp_path / "missing.pdf")


def test_non_pdf_file_is_rejected(tmp_path: Path) -> None:
    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    with pytest.raises(ValidationError):
        validate_pdf(text)


def test_zero_page_pdf_is_rejected(tmp_path: Path) -> None:
    empty = tmp_path / "zero.pdf"
    pdf = pikepdf.new()
    pages = pdf.Root.Pages
    pages["/Kids"] = pikepdf.Array()
    pages["/Count"] = 0
    pdf.save(empty)
    pdf.close()
    with pytest.raises(ValidationError):
        validate_pdf(empty)


def test_parse_page_ranges_page_count_zero() -> None:
    with pytest.raises(ValidationError):
        parse_page_ranges("1", 0)


def test_parse_page_ranges_skips_empty_members() -> None:
    assert parse_page_ranges("1,,3", 5) == [0, 2]


def test_parse_page_ranges_descending_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_page_ranges("2-1", 3)


def test_parse_page_ranges_non_numeric_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_page_ranges("abc", 3)


def test_parse_page_ranges_empty_expression_is_rejected() -> None:
    with pytest.raises(ValidationError):
        parse_page_ranges("", 3)

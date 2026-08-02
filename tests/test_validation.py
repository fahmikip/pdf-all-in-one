from pathlib import Path

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

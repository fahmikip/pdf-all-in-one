from pathlib import Path

import pymupdf
import pytest
from core.pdf.impose import impose_pages


def _multi_pdf(tmp_path: Path, pages: int = 8) -> Path:
    path = tmp_path / "multi.pdf"
    document = pymupdf.open()
    for index in range(pages):
        page = document.new_page(width=300, height=400)
        page.insert_text((40, 60), f"Page {index + 1}", fontsize=18, fontname="helv")
    document.save(path)
    document.close()
    return path


def test_two_up_sheets(sample_pdf: Path, tmp_path: Path) -> None:
    destination = tmp_path / "two.pdf"
    result = impose_pages(sample_pdf, destination, pages_per_sheet=2)
    with pymupdf.open(result) as document:
        assert document.page_count == 2
        assert document[0].rect.width == pytest.approx(600.0)
        assert document[0].rect.height == pytest.approx(400.0)
        assert "Page 1" in document[0].get_text()
        assert "Page 2" in document[0].get_text()


def test_four_up_sheets(tmp_path: Path) -> None:
    source = _multi_pdf(tmp_path, pages=5)
    destination = tmp_path / "four.pdf"
    result = impose_pages(source, destination, pages_per_sheet=4)
    with pymupdf.open(result) as document:
        assert document.page_count == 2
        text = document[0].get_text()
        assert "Page 1" in text
        assert "Page 4" in text


def test_booklet_layout(tmp_path: Path) -> None:
    source = _multi_pdf(tmp_path, pages=8)
    destination = tmp_path / "booklet.pdf"
    result = impose_pages(source, destination, booklet=True)
    with pymupdf.open(result) as document:
        assert document.page_count == 4
        assert document[0].get_text().find("Page 1") >= 0
        assert document[0].get_text().find("Page 8") >= 0
        assert document[1].get_text().find("Page 2") >= 0
        assert document[1].get_text().find("Page 7") >= 0


def test_booklet_pads_odd_counts(tmp_path: Path) -> None:
    source = _multi_pdf(tmp_path, pages=5)
    destination = tmp_path / "booklet5.pdf"
    result = impose_pages(source, destination, booklet=True)
    with pymupdf.open(result) as document:
        assert document.page_count == 4
        all_text = "".join(page.get_text() for page in document)
        assert all(f"Page {number}" in all_text for number in range(1, 6))


def test_progress_callback_reaches_100(sample_pdf: Path, tmp_path: Path) -> None:
    progress: list[int] = []
    impose_pages(
        sample_pdf, tmp_path / "p.pdf", pages_per_sheet=2, progress=lambda value, _detail: progress.append(value)
    )
    assert progress[-1] == 100


def test_invalid_pages_per_sheet_raises(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        impose_pages(sample_pdf, tmp_path / "bad.pdf", pages_per_sheet=3)


def test_destination_must_be_new_file(sample_pdf: Path) -> None:
    with pytest.raises(ValueError):
        impose_pages(sample_pdf, sample_pdf, pages_per_sheet=2)


def test_impose_rejects_non_pdf_output(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        impose_pages(sample_pdf, tmp_path / "out.txt")


def test_impose_rejects_negative_margin(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        impose_pages(sample_pdf, tmp_path / "out.pdf", margin=-1)


def test_impose_supports_full_grid_options(tmp_path: Path) -> None:
    source = _multi_pdf(tmp_path, pages=10)
    for pages_per_sheet in (1, 6, 8, 9, 16):
        result = impose_pages(source, tmp_path / f"{pages_per_sheet}.pdf", pages_per_sheet=pages_per_sheet)
        with pymupdf.open(result) as document:
            assert document.page_count >= 1

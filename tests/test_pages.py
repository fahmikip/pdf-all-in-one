from pathlib import Path

import pymupdf
import pytest
from core.pdf.pages import PAGE_SIZES, create_blank_pdf, detect_blank_pages, remove_blank_pages, resize_pages


def _mixed_blank_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "mixed.pdf"
    document = pymupdf.open()
    for index in range(3):
        page = document.new_page(width=300, height=400)
        if index != 1:
            page.insert_text((40, 60), f"Page {index + 1}", fontsize=18, fontname="helv")
    document.save(path)
    document.close()
    return path


def test_detect_blank_pages(tmp_path: Path) -> None:
    source = _mixed_blank_pdf(tmp_path)
    assert detect_blank_pages(source) == [2]


def test_detect_blank_progress(tmp_path: Path) -> None:
    source = _mixed_blank_pdf(tmp_path)
    progress: list[int] = []
    detect_blank_pages(source, progress=lambda value, _detail: progress.append(value))
    assert progress[-1] == 100


def test_remove_blank_pages(tmp_path: Path) -> None:
    source = _mixed_blank_pdf(tmp_path)
    result = remove_blank_pages(source, tmp_path / "clean.pdf")
    with pymupdf.open(result) as document:
        assert document.page_count == 2
        assert "Page 1" in document[0].get_text()
        assert "Page 3" in document[1].get_text()


def test_remove_blank_progress(tmp_path: Path) -> None:
    source = _mixed_blank_pdf(tmp_path)
    progress: list[int] = []
    remove_blank_pages(source, tmp_path / "clean.pdf", progress=lambda value, _detail: progress.append(value))
    assert progress[-1] == 100


def test_only_blank_pages_rejected(tmp_path: Path) -> None:
    path = tmp_path / "blank.pdf"
    document = pymupdf.open()
    document.new_page(width=300, height=400)
    document.save(path)
    document.close()
    with pytest.raises(ValueError):
        remove_blank_pages(path, tmp_path / "out.pdf")


def test_resize_pages_fit(sample_pdf: Path, tmp_path: Path) -> None:
    result = resize_pages(sample_pdf, tmp_path / "a4.pdf", target="A4", mode="Fit", margin=20)
    with pymupdf.open(result) as document:
        assert document.page_count == 3
        assert document[0].rect.width == pytest.approx(595.0)
        assert document[0].rect.height == pytest.approx(842.0)


def test_resize_pages_fill_and_stretch(sample_pdf: Path, tmp_path: Path) -> None:
    for mode, output_name in (("Fill", "fill.pdf"), ("Stretch", "stretch.pdf")):
        result = resize_pages(sample_pdf, tmp_path / output_name, target="Letter", mode=mode)
        with pymupdf.open(result) as document:
            assert document[0].rect.width == pytest.approx(612.0)
            assert document[0].rect.height == pytest.approx(792.0)


def test_resize_rejects_unknown_target(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resize_pages(sample_pdf, tmp_path / "out.pdf", target="Z4")


def test_resize_progress(sample_pdf: Path, tmp_path: Path) -> None:
    progress: list[int] = []
    resize_pages(
        sample_pdf,
        tmp_path / "a4.pdf",
        target="A4",
        progress=lambda value, _detail: progress.append(value),
    )
    assert progress[-1] == 100


def test_create_blank_pdf(tmp_path: Path) -> None:
    result = create_blank_pdf(tmp_path / "new.pdf", page_size="Letter", pages=2)
    with pymupdf.open(result) as document:
        assert document.page_count == 2
        assert document[0].rect.width == pytest.approx(PAGE_SIZES["Letter"][0])
        assert document[0].rect.height == pytest.approx(PAGE_SIZES["Letter"][1])


def test_create_blank_pdf_rejects_zero_pages(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        create_blank_pdf(tmp_path / "new.pdf", pages=0)
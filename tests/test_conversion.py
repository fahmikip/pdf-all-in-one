from pathlib import Path

import pymupdf
import pytest
from core.pdf.converter import images_to_pdf, pdf_to_images
from PIL import Image


def _single_image(tmp_path: Path, name: str = "photo.png") -> Path:
    path = tmp_path / name
    Image.new("RGB", (800, 600), (40, 120, 200)).save(path)
    return path


def test_images_to_pdf_and_back(tmp_path: Path) -> None:
    images = []
    for index, extension in enumerate(("png", "jpg")):
        path = tmp_path / f"image_{index}.{extension}"
        Image.new("RGB", (320 + index * 40, 240), (30, 100 + index * 50, 180)).save(path)
        images.append(path)
    pdf = images_to_pdf(images, tmp_path / "images.pdf", page_size="a4", orientation="auto", margin="small")
    with pymupdf.open(pdf) as document:
        assert document.page_count == 2
    outputs = pdf_to_images(pdf, tmp_path / "exports", image_format="webp", dpi=96, page_range="2")
    assert len(outputs) == 1
    with Image.open(outputs[0]) as result:
        assert result.format == "WEBP"


def test_pdf_to_png_selected_pages(sample_pdf: Path, tmp_path: Path) -> None:
    outputs = pdf_to_images(sample_pdf, tmp_path / "png", image_format="png", dpi=72, page_range="1,3")
    assert [path.name for path in outputs] == ["sample_page_1.png", "sample_page_3.png"]
    assert all(path.stat().st_size > 0 for path in outputs)


def test_images_to_pdf_requires_at_least_one_image(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        images_to_pdf([], tmp_path / "out.pdf")


def test_images_to_pdf_rejects_unsupported_file(tmp_path: Path) -> None:
    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError):
        images_to_pdf([text], tmp_path / "out.pdf")


def test_images_to_pdf_rejects_corrupt_image(tmp_path: Path) -> None:
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not really an image")
    with pytest.raises(ValueError):
        images_to_pdf([broken], tmp_path / "out.pdf")


def test_images_to_pdf_rejects_non_pdf_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        images_to_pdf([_single_image(tmp_path)], tmp_path / "out.txt")


def test_images_to_pdf_rejects_unknown_options(tmp_path: Path) -> None:
    image = _single_image(tmp_path)
    with pytest.raises(ValueError):
        images_to_pdf([image], tmp_path / "out.pdf", page_size="Z4")
    with pytest.raises(ValueError):
        images_to_pdf([image], tmp_path / "out.pdf", orientation="diagonal")
    with pytest.raises(ValueError):
        images_to_pdf([image], tmp_path / "out.pdf", margin="custom", custom_margin=-5)


def test_images_to_pdf_fit_size(tmp_path: Path) -> None:
    image = _single_image(tmp_path)
    result = images_to_pdf([image], tmp_path / "fit.pdf", page_size="fit")
    with pymupdf.open(result) as document:
        assert document.page_count == 1
        assert document[0].rect.width == pytest.approx(800.0)
        assert document[0].rect.height == pytest.approx(600.0)


def test_images_to_pdf_reports_progress(tmp_path: Path) -> None:
    progress: list[int] = []
    image = _single_image(tmp_path)
    images_to_pdf([image], tmp_path / "out.pdf", progress=lambda v, _d: progress.append(v))
    assert progress and progress[-1] == 100


def test_pdf_to_images_rejects_bad_options(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        pdf_to_images(sample_pdf, tmp_path, image_format="gif")
    with pytest.raises(ValueError):
        pdf_to_images(sample_pdf, tmp_path, dpi=50)
    with pytest.raises(ValueError):
        pdf_to_images(sample_pdf, tmp_path, quality=0)


def test_pdf_to_images_reports_progress(sample_pdf: Path, tmp_path: Path) -> None:
    progress: list[int] = []
    outputs = pdf_to_images(sample_pdf, tmp_path / "out", page_range="1-2", progress=lambda v, _d: progress.append(v))
    assert len(outputs) == 2
    assert progress and progress[-1] == 100

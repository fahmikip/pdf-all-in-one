from pathlib import Path

import fitz
from PIL import Image

from core.pdf.extractor import extract_images, extract_text
from core.utils.validation import ValidationError


def test_extract_text_all_pages(sample_pdf: Path, tmp_path: Path) -> None:
    output = extract_text(sample_pdf, tmp_path / "text.txt")
    content = output.read_text(encoding="utf-8")
    assert "--- Page 1 ---" in content and "--- Page 3 ---" in content
    assert "Page 1" in content and "Page 3" in content


def test_extract_text_page_range(sample_pdf: Path, tmp_path: Path) -> None:
    output = extract_text(sample_pdf, tmp_path / "text.txt", page_range="2")
    content = output.read_text(encoding="utf-8")
    assert "--- Page 2 ---" in content
    assert "--- Page 1 ---" not in content and "--- Page 3 ---" not in content


def test_extract_text_invalid_range(sample_pdf: Path, tmp_path: Path) -> None:
    try:
        extract_text(sample_pdf, tmp_path / "text.txt", page_range="9")
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


def test_extract_text_rejects_non_txt(sample_pdf: Path, tmp_path: Path) -> None:
    try:
        extract_text(sample_pdf, tmp_path / "text.pdf")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_extract_images(tmp_path: Path) -> None:
    pdf = tmp_path / "images.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=400)
    image_path = tmp_path / "photo.png"
    Image.new("RGB", (200, 150), (10, 80, 160)).save(image_path)
    page.insert_image(fitz.Rect(50, 50, 250, 200), filename=str(image_path))
    document.save(pdf)
    document.close()

    outputs = extract_images(pdf, tmp_path / "export", image_format="png")
    assert len(outputs) == 1
    with Image.open(outputs[0]) as image:
        assert image.format == "PNG"
        assert image.size == (200, 150)


def test_extract_images_jpg(tmp_path: Path) -> None:
    pdf = tmp_path / "images.pdf"
    document = fitz.open()
    page = document.new_page(width=300, height=400)
    image_path = tmp_path / "photo.png"
    Image.new("RGB", (120, 90), (200, 40, 40)).save(image_path)
    page.insert_image(fitz.Rect(40, 40, 160, 130), filename=str(image_path))
    document.save(pdf)
    document.close()

    outputs = extract_images(pdf, tmp_path / "jpg", image_format="jpg")
    assert len(outputs) == 1 and outputs[0].suffix == ".jpg"
    with Image.open(outputs[0]) as image:
        assert image.format == "JPEG"


def test_extract_images_none_found(sample_pdf: Path, tmp_path: Path) -> None:
    try:
        extract_images(sample_pdf, tmp_path / "empty")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
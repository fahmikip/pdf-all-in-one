from pathlib import Path

import fitz
from PIL import Image

from core.pdf.converter import images_to_pdf, pdf_to_images


def test_images_to_pdf_and_back(tmp_path: Path) -> None:
    images = []
    for index, extension in enumerate(("png", "jpg")):
        path = tmp_path / f"image_{index}.{extension}"
        Image.new("RGB", (320 + index * 40, 240), (30, 100 + index * 50, 180)).save(path)
        images.append(path)
    pdf = images_to_pdf(images, tmp_path / "images.pdf", page_size="a4", orientation="auto", margin="small")
    with fitz.open(pdf) as document:
        assert document.page_count == 2
    outputs = pdf_to_images(pdf, tmp_path / "exports", image_format="webp", dpi=96, page_range="2")
    assert len(outputs) == 1
    with Image.open(outputs[0]) as result:
        assert result.format == "WEBP"


def test_pdf_to_png_selected_pages(sample_pdf: Path, tmp_path: Path) -> None:
    outputs = pdf_to_images(sample_pdf, tmp_path / "png", image_format="png", dpi=72, page_range="1,3")
    assert [path.name for path in outputs] == ["sample_page_1.png", "sample_page_3.png"]
    assert all(path.stat().st_size > 0 for path in outputs)

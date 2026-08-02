from pathlib import Path

import fitz
from PIL import Image

from core.pdf.watermark import add_header_footer, add_image_watermark, add_page_numbers, add_text_watermark


def test_text_watermark_and_page_numbers(sample_pdf: Path, tmp_path: Path) -> None:
    watermarked = add_text_watermark(sample_pdf, tmp_path / "watermarked.pdf", "DRAFT", rotation=0, page_range="1-2")
    numbered = add_page_numbers(watermarked, tmp_path / "numbered.pdf", template="Page {page} / {pages}")
    with fitz.open(numbered) as document:
        assert "DRAFT" in document[0].get_text()
        assert "Page 1 / 3" in document[0].get_text()
        assert "DRAFT" not in document[2].get_text()


def test_image_watermark_and_header_placeholders(sample_pdf: Path, tmp_path: Path) -> None:
    logo = tmp_path / "logo.png"; Image.new("RGBA", (100, 50), (255, 0, 0, 255)).save(logo)
    marked = add_image_watermark(sample_pdf, tmp_path / "image_marked.pdf", logo, page_range="2")
    output = add_header_footer(marked, tmp_path / "header.pdf", {"header-left": "{filename}", "footer-right": "{page}/{pages}"})
    with fitz.open(output) as document:
        assert len(document[1].get_images()) >= 1
        assert "2/3" in document[1].get_text()

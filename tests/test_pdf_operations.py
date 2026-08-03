from pathlib import Path

import fitz
import pytest
from PIL import Image

from core.pdf.compressor import compress_pdf
from core.pdf.merger import merge_pdfs
from core.pdf.metadata import read_metadata, write_metadata
from core.pdf.page_manager import PageSpec, organize_pages, remove_pages, reorder_pages, rotate_pages
from core.pdf.splitter import extract_range, split_every_n


def page_text(path: Path) -> list[str]:
    with fitz.open(path) as document:
        return [page.get_text().strip() for page in document]


def test_merge_and_split(sample_pdf: Path, tmp_path: Path) -> None:
    merged = merge_pdfs([sample_pdf, sample_pdf], tmp_path / "merged.pdf")
    assert len(page_text(merged)) == 6
    outputs = split_every_n(merged, tmp_path / "split", 2)
    assert len(outputs) == 3
    assert all(len(page_text(path)) == 2 for path in outputs)


def test_extract_remove_reorder_rotate(sample_pdf: Path, tmp_path: Path) -> None:
    extracted = extract_range(sample_pdf, tmp_path / "extracted.pdf", "1,3")
    assert page_text(extracted) == ["Page 1", "Page 3"]
    removed = remove_pages(sample_pdf, tmp_path / "removed.pdf", [1])
    assert page_text(removed) == ["Page 1", "Page 3"]
    reordered = reorder_pages(sample_pdf, tmp_path / "reordered.pdf", [2, 0, 1, 1])
    assert page_text(reordered) == ["Page 3", "Page 1", "Page 2", "Page 2"]
    rotated = rotate_pages(sample_pdf, tmp_path / "rotated.pdf", [0, 2], 90)
    with fitz.open(rotated) as document:
        assert [page.rotation for page in document] == [90, 0, 90]


def test_original_is_protected(sample_pdf: Path, tmp_path: Path) -> None:
    before = sample_pdf.read_bytes()
    with pytest.raises(ValueError):
        remove_pages(sample_pdf, tmp_path / "bad.pdf", [0, 1, 2])
    assert sample_pdf.read_bytes() == before


def test_compress_and_metadata(sample_pdf: Path, tmp_path: Path) -> None:
    compressed = compress_pdf(sample_pdf, tmp_path / "compressed.pdf", "recommended")
    assert compressed.compressed_size > 0
    updated = write_metadata(compressed.output, tmp_path / "metadata.pdf", {"title": "Updated"})
    assert read_metadata(updated)["title"] == "Updated"


def test_image_pdf_maximum_compression_reduces_size(tmp_path: Path) -> None:
    image_path = tmp_path / "photo.bmp"
    image = Image.effect_noise((1200, 1200), 80).convert("RGB")
    image.save(image_path)
    source = tmp_path / "scan.pdf"
    with fitz.open() as document:
        page = document.new_page(width=600, height=600)
        page.insert_image(page.rect, filename=str(image_path))
        document.save(source)
    result = compress_pdf(source, tmp_path / "scan_compressed.pdf", "maximum")
    assert result.compressed_size < result.original_size
    with fitz.open(result.output) as document:
        assert document.page_count == 1


def test_aggressive_compression_produces_valid_smaller_pdf(tmp_path: Path) -> None:
    source = tmp_path / "large_scan.pdf"
    bitmap = tmp_path / "large_scan.bmp"
    Image.effect_noise((1600, 1600), 100).convert("RGB").save(bitmap)
    with fitz.open() as document:
        page = document.new_page(width=800, height=800)
        page.insert_image(page.rect, filename=str(bitmap))
        document.save(source)
    progress: list[int] = []
    result = compress_pdf(source, tmp_path / "aggressive.pdf", "maximum", aggressive=True, progress=lambda value, detail: progress.append(value))
    assert result.compressed_size < result.original_size
    assert progress[-1] == 100
    with fitz.open(result.output) as document:
        assert document.page_count == 1


def test_aggressive_compression_selects_smallest_valid_profile(tmp_path: Path) -> None:
    source = tmp_path / "scan_profiles.pdf"; bitmap = tmp_path / "scan_profiles.jpg"
    Image.effect_noise((1800, 2200), 85).convert("RGB").save(bitmap, quality=94)
    with fitz.open() as document:
        page = document.new_page(width=595, height=842); page.insert_image(page.rect, filename=str(bitmap)); document.save(source)
    maximum = compress_pdf(source, tmp_path / "maximum.pdf", "maximum", aggressive=True)
    low = compress_pdf(source, tmp_path / "low.pdf", "low", aggressive=True)
    assert maximum.compressed_size < low.compressed_size < maximum.original_size


def test_organize_pages_supports_duplicates_and_rotation(sample_pdf: Path, tmp_path: Path) -> None:
    output = organize_pages(sample_pdf, tmp_path / "organized.pdf", [PageSpec(2, 90), PageSpec(0), PageSpec(2, 180)])
    assert page_text(output) == ["Page 3", "Page 1", "Page 3"]
    with fitz.open(output) as document:
        assert [page.rotation for page in document] == [90, 0, 180]

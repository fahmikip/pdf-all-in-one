"""Lossless PDF compression with measurable results."""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import shutil

import fitz
from PIL import Image

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf


@dataclass(frozen=True, slots=True)
class CompressionResult:
    output: Path
    original_size: int
    compressed_size: int

    @property
    def saved_bytes(self) -> int:
        return max(0, self.original_size - self.compressed_size)

    @property
    def reduction_percent(self) -> float:
        return self.saved_bytes / self.original_size * 100 if self.original_size else 0.0


def _recompress_images(document: fitz.Document, level: str) -> int:
    """Replace suitable embedded images with smaller JPEG streams."""
    quality = {"low": 90, "recommended": 75, "high": 55, "maximum": 35}[level]
    processed: set[int] = set()
    replaced = 0
    for page in document:
        for image_info in page.get_images(full=True):
            xref = image_info[0]
            if xref in processed:
                continue
            processed.add(xref)
            try:
                extracted = document.extract_image(xref)
                original = extracted.get("image", b"")
                if len(original) < 16_384:
                    continue
                with Image.open(BytesIO(original)) as image:
                    if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                        continue
                    converted = image.convert("RGB")
                    buffer = BytesIO()
                    converted.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
                    candidate = buffer.getvalue()
                if len(candidate) + 1024 < len(original):
                    page.replace_image(xref, stream=candidate)
                    replaced += 1
            except (OSError, RuntimeError, ValueError):
                continue
    return replaced


def _raster_compress(document: fitz.Document, dpi: int, quality: int, progress=None) -> fitz.Document:
    """Create a smaller image-only document for explicit aggressive mode."""
    result = fitz.open()
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    for index, page in enumerate(document):
        pixmap = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB, alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        buffer = BytesIO()
        image.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
        output_page = result.new_page(width=page.rect.width, height=page.rect.height)
        output_page.insert_image(output_page.rect, stream=buffer.getvalue())
        if progress:
            progress(round((index + 1) / document.page_count * 90), f"Rasterizing page {index + 1} of {document.page_count}")
    result.set_metadata(document.metadata or {})
    return result


def compress_pdf(
    source: str | Path, destination: str | Path, level: str = "recommended",
    clean_metadata: bool = False, aggressive: bool = False, progress=None,
) -> CompressionResult:
    if level not in {"low", "recommended", "high", "maximum"}:
        raise ValueError("Unknown compression level.")
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    garbage = {"low": 1, "recommended": 3, "high": 4, "maximum": 4}[level]
    with fitz.open(info.path) as document:
        if clean_metadata:
            document.set_metadata({})
        target = _raster_compress(document, 110 if level == "maximum" else 130, 48 if level == "maximum" else 60, progress) if aggressive else document
        try:
            if not aggressive:
                _recompress_images(target, level)
            with atomic_output(output) as temporary:
                target.save(temporary, garbage=garbage, deflate=True, deflate_images=True, deflate_fonts=True, clean=level in {"high", "maximum"})
                if temporary.stat().st_size >= info.size:
                    shutil.copyfile(info.path, temporary)
        finally:
            if target is not document:
                target.close()
    if progress:
        progress(100, output.name)
    return CompressionResult(output, info.size, output.stat().st_size)

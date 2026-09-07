"""Extract text and embedded images from PDF documents."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import fitz
from PIL import Image

from core.utils.file_utils import atomic_output
from core.utils.validation import parse_page_ranges, validate_pdf

Progress = Callable[[int, str], None]


def extract_text(
    source: str | Path, destination: str | Path, *, page_range: str = "",
    progress: Progress | None = None,
) -> Path:
    """Write the PDF text to a UTF-8 text file, separated by page markers."""
    info = validate_pdf(source)
    pages = _parse_ranges(page_range, info.pages)
    output = Path(destination).expanduser().resolve()
    if output.suffix.lower() != ".txt":
        raise ValueError("Output must use the .txt extension.")
    with fitz.open(info.path) as document:
        buffers: list[str] = []
        for count, index in enumerate(pages, start=1):
            page = document[index]
            text = page.get_text("text").strip()
            buffers.append(f"--- Page {index + 1} ---\n{text}\n")
            if progress: progress(round(count / len(pages) * 100), f"Page {index + 1}")
        content = "\n".join(buffers)
    with atomic_output(output) as temporary:
        temporary.write_text(content, encoding="utf-8")
    if progress: progress(100, output.name)
    return output


def extract_images(
    source: str | Path, output_dir: str | Path, *, image_format: str = "png",
    min_size: int = 0, page_range: str = "", progress: Progress | None = None,
) -> list[Path]:
    """Extract embedded raster images from the PDF into individual files."""
    info = validate_pdf(source)
    image_format = image_format.lower()
    if image_format not in {"png", "jpg", "webp"}:
        raise ValueError("Image format must be PNG, JPG, or WebP.")
    if min_size < 0:
        raise ValueError("Minimum size must be zero or greater.")
    pages = _parse_ranges(page_range, info.pages)
    folder = Path(output_dir).expanduser().resolve(); folder.mkdir(parents=True, exist_ok=True)
    targets: list[tuple[int, list[tuple]]] = []
    with fitz.open(info.path) as document:
        for index in pages:
            targets.append((index, [item for item in document[index].get_images(full=True) if not min_size or item[2] * item[3] >= min_size]))
        total = sum(len(items) for _, items in targets)
        if not total:
            raise ValueError("No embedded images were found in the selected pages.")
        outputs: list[Path] = []
        current = 0
        for index, items in targets:
            for image_info in items:
                xref = image_info[0]
                pixmap = fitz.Pixmap(document, xref)
                if pixmap.n - pixmap.alpha > 3 or pixmap.colorspace is None:
                    pixmap = fitz.Pixmap(fitz.csRGB, pixmap)
                image = Image.frombytes("RGBA" if pixmap.alpha else "RGB", (pixmap.width, pixmap.height), pixmap.samples)
                name = f"{info.path.stem}_image_{current + 1}.{image_format}"
                file_path = folder / name
                if image_format == "png":
                    image.save(file_path, "PNG")
                else:
                    image.convert("RGB").save(file_path, "JPEG" if image_format == "jpg" else "WEBP")
                outputs.append(file_path)
                current += 1
                if progress: progress(round(current / total * 100), f"Weighted page {index + 1} · {name}")
    if progress: progress(100, f"{len(outputs)} images extracted")
    return outputs


def _parse_ranges(expression: str, page_count: int) -> list[int]:
    return parse_page_ranges(expression, page_count) if expression.strip() else list(range(page_count))
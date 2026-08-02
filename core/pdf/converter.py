"""Offline PDF/image conversion engines."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import fitz
from PIL import Image

from core.utils.file_utils import atomic_output
from core.utils.validation import parse_page_ranges, validate_pdf

Progress = Callable[[int, str], None]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
PAGE_SIZES = {
    "a4": (595.28, 841.89),
    "letter": (612.0, 792.0),
    "legal": (612.0, 1008.0),
}
MARGINS = {"none": 0.0, "small": 18.0, "medium": 36.0}


def _validated_images(paths: Sequence[str | Path]) -> list[Path]:
    if not paths:
        raise ValueError("Select at least one image.")
    result: list[Path] = []
    for value in paths:
        path = Path(value).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported or missing image: {path.name}")
        try:
            with Image.open(path) as image:
                image.verify()
        except Exception as exc:
            raise ValueError(f"The image cannot be read: {path.name}") from exc
        result.append(path)
    return result


def images_to_pdf(
    sources: Sequence[str | Path], destination: str | Path, *, page_size: str = "a4",
    orientation: str = "auto", margin: str = "small", custom_margin: float = 18.0,
    progress: Progress | None = None,
) -> Path:
    images = _validated_images(sources)
    output = Path(destination).expanduser().resolve()
    if output.suffix.lower() != ".pdf":
        raise ValueError("Output must use the .pdf extension.")
    if page_size not in {*PAGE_SIZES, "fit"}:
        raise ValueError("Unknown page size.")
    if orientation not in {"auto", "portrait", "landscape"}:
        raise ValueError("Unknown orientation.")
    margin_points = custom_margin if margin == "custom" else MARGINS.get(margin)
    if margin_points is None or margin_points < 0:
        raise ValueError("Margin must be zero or greater.")
    document = fitz.open()
    try:
        for index, image_path in enumerate(images):
            with Image.open(image_path) as image:
                width_px, height_px = image.size
            if page_size == "fit":
                width, height = float(width_px), float(height_px)
            else:
                width, height = PAGE_SIZES[page_size]
                landscape = orientation == "landscape" or (orientation == "auto" and width_px > height_px)
                if landscape and width < height or not landscape and width > height:
                    width, height = height, width
            page = document.new_page(width=width, height=height)
            available = fitz.Rect(margin_points, margin_points, width - margin_points, height - margin_points)
            scale = min(available.width / width_px, available.height / height_px)
            draw_width, draw_height = width_px * scale, height_px * scale
            left = (width - draw_width) / 2; top = (height - draw_height) / 2
            page.insert_image(fitz.Rect(left, top, left + draw_width, top + draw_height), filename=str(image_path), keep_proportion=True)
            if progress: progress(round((index + 1) / len(images) * 95), image_path.name)
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    finally:
        document.close()
    if progress: progress(100, output.name)
    return output


def pdf_to_images(
    source: str | Path, output_dir: str | Path, *, image_format: str = "png", dpi: int = 150,
    quality: int = 90, page_range: str = "", transparent: bool = False,
    progress: Progress | None = None,
) -> list[Path]:
    info = validate_pdf(source)
    image_format = image_format.lower()
    if image_format not in {"jpg", "png", "webp"}:
        raise ValueError("Image format must be JPG, PNG, or WebP.")
    if dpi < 72 or dpi > 600:
        raise ValueError("DPI must be between 72 and 600.")
    if quality < 1 or quality > 100:
        raise ValueError("Quality must be between 1 and 100.")
    pages = parse_page_ranges(page_range, info.pages) if page_range.strip() else list(range(info.pages))
    folder = Path(output_dir).expanduser().resolve(); folder.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    with fitz.open(info.path) as document:
        for count, index in enumerate(pages, start=1):
            pixmap = document[index].get_pixmap(matrix=matrix, alpha=transparent and image_format in {"png", "webp"}, colorspace=fitz.csRGB)
            mode = "RGBA" if pixmap.alpha else "RGB"
            image = Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples)
            output = folder / f"{info.path.stem}_page_{index + 1}.{image_format}"
            save_format = "JPEG" if image_format == "jpg" else image_format.upper()
            options = {"quality": quality} if image_format in {"jpg", "webp"} else {"compress_level": 6}
            image.save(output, save_format, **options)
            outputs.append(output)
            if progress: progress(round(count / len(pages) * 100), f"Page {index + 1}")
    return outputs

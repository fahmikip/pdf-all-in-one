"""Watermark, page numbering, and header/footer operations."""
from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Mapping

import fitz
from PIL import Image

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import parse_page_ranges, validate_pdf

POSITIONS = {"top-left", "top-center", "top-right", "center", "bottom-left", "bottom-center", "bottom-right"}


def _pages(expression: str, count: int) -> list[int]:
    return parse_page_ranges(expression, count) if expression.strip() else list(range(count))


def _point(rect: fitz.Rect, position: str, margin: float, width: float, height: float) -> tuple[float, float]:
    horizontal = position.rsplit("-", 1)[-1] if position != "center" else "center"
    vertical = position.split("-", 1)[0] if position != "center" else "center"
    x = margin if horizontal == "left" else rect.width - margin - width if horizontal == "right" else (rect.width - width) / 2
    y = margin if vertical == "top" else rect.height - margin - height if vertical == "bottom" else (rect.height - height) / 2
    return x, y


def add_text_watermark(source: str | Path, destination: str | Path, text: str, *, font_size: float = 36, opacity: float = .25, rotation: int = 0, position: str = "center", margin: float = 24, page_range: str = "") -> Path:
    info = validate_pdf(source); output = Path(destination).resolve(); ensure_distinct_paths(info.path, output)
    if not text.strip(): raise ValueError("Watermark text cannot be empty.")
    if position not in POSITIONS or rotation not in {0, 90, 180, 270}: raise ValueError("Invalid watermark position or rotation.")
    with fitz.open(info.path) as document:
        for index in _pages(page_range, info.pages):
            page = document[index]; width = min(page.rect.width - 2 * margin, max(180, len(text) * font_size * .65)); height = font_size * 2
            x, y = _point(page.rect, position, margin, width, height)
            page.insert_textbox(fitz.Rect(x, y, x + width, y + height), text, fontsize=font_size, color=(.35, .35, .4), align=fitz.TEXT_ALIGN_CENTER, rotate=rotation, fill_opacity=max(0, min(1, opacity)), overlay=True)
        with atomic_output(output) as temporary: document.save(temporary, garbage=3, deflate=True)
    return output


def add_image_watermark(source: str | Path, destination: str | Path, image_path: str | Path, *, opacity: float = .3, scale: float = .25, position: str = "center", margin: float = 24, page_range: str = "") -> Path:
    info = validate_pdf(source); output = Path(destination).resolve(); ensure_distinct_paths(info.path, output)
    image_source = Path(image_path).resolve()
    if not image_source.is_file(): raise ValueError("Watermark image does not exist.")
    with Image.open(image_source) as image:
        rgba = image.convert("RGBA"); alpha = rgba.getchannel("A").point(lambda value: int(value * max(0, min(1, opacity)))); rgba.putalpha(alpha)
        stream = BytesIO(); rgba.save(stream, "PNG"); image_bytes = stream.getvalue(); ratio = rgba.height / rgba.width
    with fitz.open(info.path) as document:
        for index in _pages(page_range, info.pages):
            page = document[index]; width = page.rect.width * max(.05, min(.9, scale)); height = width * ratio
            x, y = _point(page.rect, position, margin, width, height)
            page.insert_image(fitz.Rect(x, y, x + width, y + height), stream=image_bytes, overlay=True, keep_proportion=True)
        with atomic_output(output) as temporary: document.save(temporary, garbage=3, deflate=True)
    return output


def place_image(source: str | Path, destination: str | Path, image_path: str | Path, *, position: str = "center", width_scale: float = .5, margin: float = 24, page_range: str = "1", progress=None) -> Path:
    """Insert a photo (JPEG/PNG/…) onto one or more pages at a chosen position."""
    info = validate_pdf(source); output = Path(destination).resolve(); ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".pdf": raise ValueError("Insert image output must use .pdf.")
    if position not in POSITIONS: raise ValueError("Invalid image position.")
    if not 0 < width_scale <= 1: raise ValueError("Image width scale must be between 0 and 1.")
    image_source = Path(image_path).resolve()
    if not image_source.is_file(): raise ValueError("Image file does not exist.")
    with Image.open(image_source) as image:
        image.verify()
    with Image.open(image_source) as image:
        ratio = image.height / image.width
    with fitz.open(info.path) as document:
        selected = _pages(page_range, info.pages)
        for sequence, index in enumerate(selected):
            page = document[index]; width = page.rect.width * width_scale; height = width * ratio
            x, y = _point(page.rect, position, margin, width, height)
            page.insert_image(fitz.Rect(x, y, x + width, y + height), filename=str(image_source), overlay=True, keep_proportion=True)
            if progress: progress(round((sequence + 1) / len(selected) * 95), f"Placed image on page {index + 1}")
        with atomic_output(output) as temporary: document.save(temporary, garbage=3, deflate=True)
    if progress: progress(100, output.name)
    return output


def add_page_numbers(source: str | Path, destination: str | Path, *, template: str = "{page} / {pages}", position: str = "bottom-center", font_size: float = 10, margin: float = 24, start_number: int = 1, page_range: str = "") -> Path:
    info = validate_pdf(source); output = Path(destination).resolve(); ensure_distinct_paths(info.path, output)
    with fitz.open(info.path) as document:
        selected = _pages(page_range, info.pages)
        for sequence, index in enumerate(selected):
            text = template.format(page=start_number + sequence, pages=len(selected)); page = document[index]; width, height = 150, font_size * 1.8
            x, y = _point(page.rect, position, margin, width, height)
            page.insert_textbox(fitz.Rect(x, y, x + width, y + height), text, fontsize=font_size, align=fitz.TEXT_ALIGN_CENTER, color=(.15, .15, .18), overlay=True)
        with atomic_output(output) as temporary: document.save(temporary, garbage=3, deflate=True)
    return output


def add_header_footer(source: str | Path, destination: str | Path, fields: Mapping[str, str], *, font_size: float = 9, margin: float = 22, page_range: str = "") -> Path:
    info = validate_pdf(source); output = Path(destination).resolve(); ensure_distinct_paths(info.path, output)
    valid = {"header-left", "header-center", "header-right", "footer-left", "footer-center", "footer-right"}
    with fitz.open(info.path) as document:
        selected = _pages(page_range, info.pages)
        for index in selected:
            page = document[index]
            replacements = {"page": str(index + 1), "pages": str(info.pages), "date": date.today().isoformat(), "filename": info.path.name}
            for key, template in fields.items():
                if key not in valid or not template: continue
                text = template
                for placeholder, value in replacements.items(): text = text.replace("{" + placeholder + "}", value)
                vertical, horizontal = key.split("-"); position = f"{'top' if vertical == 'header' else 'bottom'}-{horizontal}"
                width, height = 180, font_size * 1.8; x, y = _point(page.rect, position, margin, width, height)
                align = {"left": fitz.TEXT_ALIGN_LEFT, "center": fitz.TEXT_ALIGN_CENTER, "right": fitz.TEXT_ALIGN_RIGHT}[horizontal]
                page.insert_textbox(fitz.Rect(x, y, x + width, y + height), text, fontsize=font_size, align=align, overlay=True)
        with atomic_output(output) as temporary: document.save(temporary, garbage=3, deflate=True)
    return output

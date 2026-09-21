"""Watermark, page numbering, and header/footer operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.fonts import resolve_font
from core.utils.validation import parse_page_ranges, validate_pdf

POSITIONS = {"top-left", "top-center", "top-right", "center", "bottom-left", "bottom-center", "bottom-right"}


def _pages(expression: str, count: int) -> list[int]:
    return parse_page_ranges(expression, count) if expression.strip() else list(range(count))


def _point(rect: pymupdf.Rect, position: str, margin: float, width: float, height: float) -> tuple[float, float]:
    horizontal = position.rsplit("-", 1)[-1] if position != "center" else "center"
    vertical = position.split("-", 1)[0] if position != "center" else "center"
    x = (
        margin
        if horizontal == "left"
        else rect.width - margin - width
        if horizontal == "right"
        else (rect.width - width) / 2
    )
    y = (
        margin
        if vertical == "top"
        else rect.height - margin - height
        if vertical == "bottom"
        else (rect.height - height) / 2
    )
    return x, y


def add_text_watermark(
    source: str | Path,
    destination: str | Path,
    text: str,
    *,
    font_size: float = 36,
    opacity: float = 0.25,
    rotation: int = 0,
    position: str = "center",
    margin: float = 24,
    page_range: str = "",
) -> Path:
    info = validate_pdf(source)
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    if not text.strip():
        raise ValueError("Watermark text cannot be empty.")
    if position not in POSITIONS or rotation not in {0, 90, 180, 270}:
        raise ValueError("Invalid watermark position or rotation.")
    with pymupdf.open(info.path) as document:
        for index in _pages(page_range, info.pages):
            page = document[index]
            width = min(page.rect.width - 2 * margin, max(180, len(text) * font_size * 0.65))
            height = font_size * 2
            x, y = _point(page.rect, position, margin, width, height)
            page.insert_textbox(
                pymupdf.Rect(x, y, x + width, y + height),
                text,
                fontsize=font_size,
                color=(0.35, 0.35, 0.4),
                align=pymupdf.TEXT_ALIGN_CENTER,
                rotate=rotation,
                fill_opacity=max(0, min(1, opacity)),
                overlay=True,
            )
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    return output


def add_image_watermark(
    source: str | Path,
    destination: str | Path,
    image_path: str | Path,
    *,
    opacity: float = 0.3,
    scale: float = 0.25,
    position: str = "center",
    margin: float = 24,
    page_range: str = "",
) -> Path:
    info = validate_pdf(source)
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    image_source = Path(image_path).resolve()
    if not image_source.is_file():
        raise ValueError("Watermark image does not exist.")
    with Image.open(image_source) as image:
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A").point(lambda value: int(value * max(0, min(1, opacity))))
        rgba.putalpha(alpha)
        stream = BytesIO()
        rgba.save(stream, "PNG")
        image_bytes = stream.getvalue()
        ratio = rgba.height / rgba.width
    with pymupdf.open(info.path) as document:
        for index in _pages(page_range, info.pages):
            page = document[index]
            width = page.rect.width * max(0.05, min(0.9, scale))
            height = width * ratio
            x, y = _point(page.rect, position, margin, width, height)
            page.insert_image(
                pymupdf.Rect(x, y, x + width, y + height), stream=image_bytes, overlay=True, keep_proportion=True
            )
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    return output


def place_image(
    source: str | Path,
    destination: str | Path,
    image_path: str | Path,
    *,
    position: str = "center",
    width_scale: float = 0.5,
    margin: float = 24,
    page_range: str = "1",
    progress=None,
) -> Path:
    """Insert a photo (JPEG/PNG/…) onto one or more pages at a chosen position."""
    info = validate_pdf(source)
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".pdf":
        raise ValueError("Insert image output must use .pdf.")
    if position not in POSITIONS:
        raise ValueError("Invalid image position.")
    if not 0 < width_scale <= 1:
        raise ValueError("Image width scale must be between 0 and 1.")
    image_source = Path(image_path).resolve()
    if not image_source.is_file():
        raise ValueError("Image file does not exist.")
    with Image.open(image_source) as image:
        image.verify()
    with Image.open(image_source) as image:
        ratio = image.height / image.width
    with pymupdf.open(info.path) as document:
        selected = _pages(page_range, info.pages)
        for sequence, index in enumerate(selected):
            page = document[index]
            width = page.rect.width * width_scale
            height = width * ratio
            x, y = _point(page.rect, position, margin, width, height)
            page.insert_image(
                pymupdf.Rect(x, y, x + width, y + height),
                filename=str(image_source),
                overlay=True,
                keep_proportion=True,
            )
            if progress:
                progress(round((sequence + 1) / len(selected) * 95), f"Placed image on page {index + 1}")
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    if progress:
        progress(100, output.name)
    return output


def insert_objects(
    source: str | Path,
    destination: str | Path,
    *,
    page_index: int | None = None,
    items: list[Mapping] | None = None,
    page_items: Mapping[int, Sequence[Mapping]] | None = None,
    progress=None,
) -> Path:
    """Render interactive editor objects onto one or more pages of a PDF.

    ``page_items`` maps zero-based page indices to object descriptors. When
    ``page_items`` is omitted, ``items`` is applied to ``page_index`` (default 0)
    for backwards compatibility.
    """
    info = validate_pdf(source)
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    if page_items is None:
        page_items = {page_index or 0: items or []}
    for index in page_items:
        if not 0 <= index < info.pages:
            raise ValueError(f"Page {index + 1} does not exist.")
    align_map = {
        "left": pymupdf.TEXT_ALIGN_LEFT,
        "center": pymupdf.TEXT_ALIGN_CENTER,
        "right": pymupdf.TEXT_ALIGN_RIGHT,
    }
    total = sum(len(objects) for objects in page_items.values())
    processed = 0
    with pymupdf.open(info.path) as document:
        for index, objects in page_items.items():
            page = document[index]
            for item in objects:
                if "rect" not in item:
                    continue
                rect = pymupdf.Rect(*item["rect"])
                if rect.width <= 0 or rect.height <= 0:
                    continue
                rotation = int(item.get("rotation") or 0)
                opacity = max(0.0, min(1.0, float(item.get("opacity", 1.0))))
                kind = item.get("type")
                if kind == "image":
                    image_source = Path(item["image"]).resolve()
                    if not image_source.is_file():
                        raise ValueError(f"Image file does not exist: {image_source.name}")
                    with Image.open(image_source) as image:
                        image = image.convert("RGBA")
                        if opacity < 1.0:
                            alpha = image.getchannel("A").point(lambda value, factor=opacity: int(value * factor))
                            image.putalpha(alpha)
                        if rotation:
                            image = image.rotate(-rotation, expand=True)
                        stream = BytesIO()
                        image.save(stream, "PNG")
                        image_bytes = stream.getvalue()
                    page.insert_image(rect, stream=image_bytes, overlay=True, keep_proportion=True)
                elif kind == "text" and item.get("text"):
                    color = tuple(max(0, min(1, channel / 255)) for channel in item.get("color", (0, 0, 0)))
                    fontname = "helv"
                    fontfile = None
                    set_simple = 0
                    if resolved := resolve_font(item.get("font", "")):
                        fontname = "f0"
                        fontfile = str(resolved)
                        set_simple = 1
                    text = item["text"]
                    align = align_map.get(item.get("align", "left"), pymupdf.TEXT_ALIGN_LEFT)
                    kwargs = {
                        "fontsize": max(1, item.get("size", 12)),
                        "fontname": fontname,
                        "fontfile": fontfile,
                        "color": color,
                        "set_simple": set_simple,
                        "fill_opacity": opacity,
                        "overlay": True,
                    }
                    if rotation:
                        page.insert_text(
                            (rect.x0, rect.y0 + rect.height * 0.62),
                            text.split("\n"),
                            rotate=rotation,
                            **kwargs,
                        )
                    elif "\n" in text:
                        unused = page.insert_textbox(rect, text, align=align, **kwargs)
                        if unused < 0:
                            page.insert_text(
                                (rect.x0, rect.y0 + rect.height * 0.72),
                                text.split("\n"),
                                lineheight=1.2,
                                **kwargs,
                            )
                    else:
                        page.insert_text((rect.x0, rect.y0 + rect.height * 0.72), text, **kwargs)
                processed += 1
                if progress:
                    progress(round(processed / max(total, 1) * 95), f"Menempatkan objek {processed}/{total}…")
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    if progress:
        progress(100, output.name)
    return output


def add_page_numbers(
    source: str | Path,
    destination: str | Path,
    *,
    template: str = "{page} / {pages}",
    position: str = "bottom-center",
    font_size: float = 10,
    margin: float = 24,
    start_number: int = 1,
    page_range: str = "",
) -> Path:
    info = validate_pdf(source)
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    with pymupdf.open(info.path) as document:
        selected = _pages(page_range, info.pages)
        for sequence, index in enumerate(selected):
            text = template.format(page=start_number + sequence, pages=len(selected))
            page = document[index]
            width, height = 150, font_size * 1.8
            x, y = _point(page.rect, position, margin, width, height)
            page.insert_textbox(
                pymupdf.Rect(x, y, x + width, y + height),
                text,
                fontsize=font_size,
                align=pymupdf.TEXT_ALIGN_CENTER,
                color=(0.15, 0.15, 0.18),
                overlay=True,
            )
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    return output


def add_header_footer(
    source: str | Path,
    destination: str | Path,
    fields: Mapping[str, str],
    *,
    font_size: float = 9,
    margin: float = 22,
    page_range: str = "",
) -> Path:
    info = validate_pdf(source)
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    valid = {"header-left", "header-center", "header-right", "footer-left", "footer-center", "footer-right"}
    with pymupdf.open(info.path) as document:
        selected = _pages(page_range, info.pages)
        for index in selected:
            page = document[index]
            replacements = {
                "page": str(index + 1),
                "pages": str(info.pages),
                "date": date.today().isoformat(),
                "filename": info.path.name,
            }
            for key, template in fields.items():
                if key not in valid or not template:
                    continue
                text = template
                for placeholder, value in replacements.items():
                    text = text.replace("{" + placeholder + "}", value)
                vertical, horizontal = key.split("-")
                position = f"{'top' if vertical == 'header' else 'bottom'}-{horizontal}"
                width, height = 180, font_size * 1.8
                x, y = _point(page.rect, position, margin, width, height)
                align = {
                    "left": pymupdf.TEXT_ALIGN_LEFT,
                    "center": pymupdf.TEXT_ALIGN_CENTER,
                    "right": pymupdf.TEXT_ALIGN_RIGHT,
                }[horizontal]
                page.insert_textbox(
                    pymupdf.Rect(x, y, x + width, y + height), text, fontsize=font_size, align=align, overlay=True
                )
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    return output

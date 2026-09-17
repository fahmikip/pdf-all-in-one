"""Blank-page cleanup, standard-size resizing, and new blank document creation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pymupdf

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf

Progress = Callable[[int, str], None]

PAGE_SIZES: dict[str, tuple[float, float]] = {
    "A5": (419.53, 595.28),
    "A4": (595.0, 842.0),
    "A4 Landscape": (842.0, 595.0),
    "A3": (841.89, 1190.55),
    "Letter": (612.0, 792.0),
    "Letter Landscape": (792.0, 612.0),
    "Legal": (612.0, 1008.0),
}

FIT_MODES = ("Fit", "Fill", "Stretch")


def is_blank_page(page: pymupdf.Page) -> bool:
    """Return True when a page carries no text, image, or vector content."""
    return not page.get_text().strip() and not page.get_images(full=True) and not page.get_drawings()


def detect_blank_pages(source: str | Path, *, progress: Progress | None = None) -> list[int]:
    """Return the one-based page numbers that are visually blank."""
    info = validate_pdf(source)
    if info.encrypted:
        raise ValueError("Blank-page detection requires an unlocked PDF.")
    blanks: list[int] = []
    with pymupdf.open(info.path) as document:
        for index, page in enumerate(document):
            if is_blank_page(page):
                blanks.append(index + 1)
            if progress:
                progress(
                    round((index + 1) / document.page_count * 95),
                    f"Checked page {index + 1} of {document.page_count}",
                )
    if progress:
        progress(100, f"{len(blanks)} blank page(s) found")
    return blanks


def remove_blank_pages(source: str | Path, destination: str | Path, *, progress: Progress | None = None) -> Path:
    """Write a copy of the PDF without its blank pages."""
    info = validate_pdf(source)
    if info.encrypted:
        raise ValueError("Blank-page removal requires an unlocked PDF.")
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".pdf":
        raise ValueError("Blank-page removal output must use .pdf.")
    with pymupdf.open(info.path) as document:
        blank_indices = [index for index, page in enumerate(document) if is_blank_page(page)]
        removed = set(blank_indices)
        remaining = [index for index in range(document.page_count) if index not in removed]
        if not remaining:
            raise ValueError("The PDF only contains blank pages; nothing can be kept.")
        with pymupdf.open() as result:
            for kept_index, index in enumerate(remaining):
                result.insert_pdf(document, from_page=index, to_page=index)
                if progress:
                    progress(round((kept_index + 1) / len(remaining) * 90), "Rebuilding document…")
            with atomic_output(output) as temporary:
                result.save(temporary, garbage=3, deflate=True)
    if progress:
        progress(100, f"Removed {len(blank_indices)} blank page(s)")
    return output


def _resize_geometry(
    target_width: float,
    target_height: float,
    source_width: float,
    source_height: float,
    mode: str,
    margin: float,
) -> tuple[pymupdf.Rect, pymupdf.Rect | None, bool]:
    inset = max(0.0, margin)
    rect = pymupdf.Rect(
        inset,
        inset,
        max(inset + 1.0, target_width - inset),
        max(inset + 1.0, target_height - inset),
    )
    if mode == "Stretch":
        return rect, None, False
    if mode not in ("Fit", "Fill"):
        raise ValueError("Fit mode must be one of: Fit, Fill, Stretch.")
    available_w = max(1.0, target_width - 2 * inset)
    available_h = max(1.0, target_height - 2 * inset)
    ratio_w = available_w / source_width
    ratio_h = available_h / source_height
    scale = min(ratio_w, ratio_h) if mode == "Fit" else max(ratio_w, ratio_h)
    if mode == "Fill":
        clip_width = available_w / scale
        clip_height = available_h / scale
        left = (source_width - clip_width) / 2
        top = (source_height - clip_height) / 2
        clip = pymupdf.Rect(left, top, left + clip_width, top + clip_height)
        return rect, clip, False
    return rect, None, True


def resize_pages(
    source: str | Path,
    destination: str | Path,
    *,
    target: str = "A4",
    mode: str = "Fit",
    margin: float = 0.0,
    progress: Progress | None = None,
) -> Path:
    """Rebuild the PDF on pages of a standard size, scaling each page's content."""
    info = validate_pdf(source)
    if info.encrypted:
        raise ValueError("Resizing requires an unlocked PDF.")
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".pdf":
        raise ValueError("Resize output must use .pdf.")
    if target not in PAGE_SIZES:
        raise ValueError("Unknown page size target.")
    if mode not in ("Fit", "Fill", "Stretch"):
        raise ValueError("Fit mode must be one of: Fit, Fill, Stretch.")
    width, height = PAGE_SIZES[target]
    with pymupdf.open(info.path) as document, pymupdf.open() as result:
        count = document.page_count
        for index, page in enumerate(document):
            result.new_page(width=width, height=height)
            target_page = result[-1]
            rect, clip, keep = _resize_geometry(
                width, height, page.rect.width, page.rect.height, mode, margin
            )
            target_page.show_pdf_page(
                rect,
                document,
                pno=index,
                keep_proportion=keep,
                clip=clip,
            )
            if progress:
                progress(
                    round((index + 1) / count * 90),
                    f"Resized page {index + 1} of {count}",
                )
        with atomic_output(output) as temporary:
            result.save(temporary, garbage=3, deflate=True)
    if progress:
        progress(100, output.name)
    return output


def create_blank_pdf(destination: str | Path, *, page_size: str = "A4", pages: int = 1) -> Path:
    """Create a new empty PDF with the requested standard page size."""
    output = Path(destination).expanduser().resolve()
    if pages < 1:
        raise ValueError("Create at least one page.")
    if page_size not in PAGE_SIZES:
        raise ValueError("Unknown page size.")
    width, height = PAGE_SIZES[page_size]
    with pymupdf.open() as document:
        for _ in range(int(pages)):
            document.new_page(width=width, height=height)
        with atomic_output(output) as temporary:
            document.save(temporary)
    return output